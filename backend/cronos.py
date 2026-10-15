import os
import io
import csv
import re
import uuid
import httpx
import calendar
import logging
import unicodedata
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from html import escape
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field
from db import db
from auth import get_current_user, require_admin, audit, admin_emails, role_for
from emailer import send_email, EMAIL_FROM_NAME

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Madrid")
TYPES = ["desarrollo", "corrección", "consulta", "pruebas"]
PHASES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "otra"]
SOURCES = ["estimado", "confirmado", "importado"]
LINE_FORMAT = "#cronos | título | tipo | fase | minutos | mensajes | créditos [| proyecto]"
DEFAULT_MODELS = ["Claude Fable 5.1", "Claude Sonnet 4.5", "Claude Opus 4.1", "GPT-5", "GPT-4.1", "Gemini 2.5 Pro", "Gemini 2.5 Flash"]
DEFAULT_SETTINGS = {"price_per_credit_eur": 0.01, "monthly_budget_credits": 5000, "alerts_sent": {}, "phase_goals": {}, "models": DEFAULT_MODELS,
                    "sync_sources": [], "last_sync": None}
ENTRY_FIELDS = ["title", "project", "type", "phase", "date", "minutes", "messages", "credits",
                "source", "notes", "estimated_credits", "user", "model"]
NO_ID = {"_id": 0}

router = APIRouter(prefix="/api/cronos")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_local() -> date:
    return datetime.now(TZ).date()


def valid_date(s: Any) -> bool:
    try:
        date.fromisoformat(str(s))
        return True
    except Exception:
        return False


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def validate_enums(d: dict):
    if "type" in d and d["type"] not in TYPES:
        raise HTTPException(422, f"Tipo no válido. Valores: {', '.join(TYPES)}")
    if "phase" in d and d["phase"] not in PHASES:
        raise HTTPException(422, f"Fase no válida. Valores: {', '.join(PHASES)}")
    if "source" in d and d["source"] not in SOURCES:
        raise HTTPException(422, f"Origen no válido. Valores: {', '.join(SOURCES)}")
    if "date" in d and not valid_date(d["date"]):
        raise HTTPException(422, "Fecha no válida. Usa el formato AAAA-MM-DD")


# ---------- settings ----------
async def get_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    async for doc in db.cronos_settings.find({}, NO_ID):
        s[doc["key"]] = doc["value"]
    return s


async def set_setting(key: str, value: Any):
    await db.cronos_settings.update_one({"key": key}, {"$set": {"key": key, "value": value}}, upsert=True)


async def ensure_defaults():
    for k, v in DEFAULT_SETTINGS.items():
        if not await db.cronos_settings.find_one({"key": k}):
            await set_setting(k, v)
    seed_user = (os.environ.get("ADMIN_EMAILS", "").split(",")[0] or "").strip().lower()
    await db.cronos_entries.update_many({"user": {"$in": [None, ""]}}, {"$set": {"user": seed_user}})
    await db.cronos_entries.update_many({"model": None}, {"$set": {"model": ""}})


async def ensure_project(name: str):
    if name and not await db.cronos_projects.find_one({"name": name}):
        await db.cronos_projects.insert_one({"id": str(uuid.uuid4()), "name": name, "monthly_goal_credits": None,
                                            "goal_credits": None, "color": None, "archived": False})


# ---------- filters ----------
class Filters:
    def __init__(self, project: Optional[str] = None, type: Optional[str] = None, phase: Optional[str] = None,
                 source: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
                 user: Optional[str] = None, model: Optional[str] = None):
        q: dict = {}
        if project:
            q["project"] = project
        if type:
            q["type"] = type
        if phase:
            q["phase"] = phase
        if source:
            q["source"] = source
        if user:
            q["user"] = user
        if model:
            q["model"] = model
        if date_from or date_to:
            q["date"] = {}
            if date_from:
                q["date"]["$gte"] = date_from
            if date_to:
                q["date"]["$lte"] = date_to
        self.query = q


async def fetch_entries(query: dict) -> list:
    return await db.cronos_entries.find(query, NO_ID).sort([("date", -1), ("created_at", -1)]).to_list(10000)


# ---------- stats ----------
def agg(entries: list, key: str, price: float) -> list:
    out: dict = {}
    for e in entries:
        k = e.get(key) or "—"
        a = out.setdefault(k, {"key": k, "count": 0, "credits": 0.0, "minutes": 0, "messages": 0})
        a["count"] += 1
        a["credits"] += float(e.get("credits") or 0)
        a["minutes"] += int(e.get("minutes") or 0)
        a["messages"] += int(e.get("messages") or 0)
    for a in out.values():
        a["credits"] = round(a["credits"], 2)
        a["cost_eur"] = round(a["credits"] * price, 2)
    return sorted(out.values(), key=lambda x: -x["credits"])


def compute_stats(entries: list, price: float) -> dict:
    n = len(entries)
    credits = round(sum(float(e.get("credits") or 0) for e in entries), 2)
    minutes = sum(int(e.get("minutes") or 0) for e in entries)
    messages = sum(int(e.get("messages") or 0) for e in entries)

    def block(lst):
        c = round(sum(float(e.get("credits") or 0) for e in lst), 2)
        return {"count": len(lst), "credits": c, "cost_eur": round(c * price, 2),
                "minutes": sum(int(e.get("minutes") or 0) for e in lst)}

    corr = block([e for e in entries if e.get("type") == "corrección"])
    dev = block([e for e in entries if e.get("type") == "desarrollo"])
    tot = corr["credits"] + dev["credits"]
    daily = sorted(agg(entries, "date", price), key=lambda x: x["key"])
    for d in daily:
        d["date"] = d.pop("key")
    top = sorted(entries, key=lambda e: -float(e.get("credits") or 0))[:8]
    monthly = []
    for m in sorted(agg([{**e, "month": str(e.get("date", ""))[:7]} for e in entries], "month", price), key=lambda x: x["key"]):
        m["month"] = m.pop("key")
        m["hours"] = round(m["minutes"] / 60, 2)
        if monthly:
            prev = monthly[-1]["credits"]
            m["delta_pct"] = round((m["credits"] - prev) / prev * 100, 1) if prev else None
        else:
            m["delta_pct"] = None
        monthly.append(m)
    return {
        "count": n, "credits": credits, "cost_eur": round(credits * price, 2),
        "minutes": minutes, "hours": round(minutes / 60, 2), "messages": messages,
        "avg_credits_per_task": round(credits / n, 2) if n else 0,
        "avg_minutes_per_task": round(minutes / n, 1) if n else 0,
        "credits_per_message": round(credits / messages, 2) if messages else 0,
        "credits_per_minute": round(credits / minutes, 2) if minutes else 0,
        "comparison": {"correccion": corr, "desarrollo": dev,
                       "correccion_pct": round(corr["credits"] / tot * 100, 1) if tot else 0},
        "by_type": agg(entries, "type", price), "by_phase": agg(entries, "phase", price),
        "by_source": agg(entries, "source", price), "daily": daily, "top": top, "monthly": monthly,
        "by_model": agg(entries, "model", price), "by_user": agg(entries, "user", price),
        "price_per_credit_eur": price,
    }


# ---------- parsing ----------
def parse_number(raw: str) -> Optional[float]:
    s = re.sub(r"[^\d,.\-]", "", raw or "")
    if not s or not any(ch.isdigit() for ch in s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        parts = s.split(sep)
        if len(parts) == 2 and len(parts[1]) == 3 and parts[0].lstrip("-") not in ("", "0"):
            s = s.replace(sep, "")
        else:
            s = s.replace(sep, ".")
    try:
        return abs(float(s))
    except ValueError:
        return None


def normalize_type(raw: str) -> Optional[str]:
    t = strip_accents(raw.strip().lower())
    table = {"desarrollo": "desarrollo", "dev": "desarrollo", "development": "desarrollo", "feature": "desarrollo",
             "correccion": "corrección", "fix": "corrección", "bug": "corrección", "bugfix": "corrección",
             "consulta": "consulta", "pregunta": "consulta", "question": "consulta",
             "pruebas": "pruebas", "test": "pruebas", "tests": "pruebas", "testing": "pruebas", "qa": "pruebas"}
    return table.get(t)


def normalize_phase(raw: str) -> str:
    m = re.search(r"[pP]?\s*([1-7])\b", raw.strip())
    return f"P{m.group(1)}" if m else "otra"


def parse_cronos_line(line: str) -> dict:
    parts = [p.strip() for p in line.strip().split("|")]
    if not strip_accents(parts[0].lower()).startswith("#cronos"):
        raise HTTPException(400, f"La línea debe empezar por «#cronos». Formato: {LINE_FORMAT}")
    parts = parts[1:]
    if len(parts) < 6:
        raise HTTPException(400, f"Faltan campos ({len(parts)} de 6). Formato: {LINE_FORMAT}")
    warnings: list = []
    title, type_raw, phase_raw, min_raw, msg_raw, cr_raw = parts[:6]
    project = parts[6] if len(parts) > 6 else ""
    model = parts[7] if len(parts) > 7 else ""
    typ = normalize_type(type_raw)
    if not typ:
        typ = "desarrollo"
        warnings.append(f"Tipo «{type_raw}» no reconocido; se usa «desarrollo»")
    phase = normalize_phase(phase_raw)
    if phase == "otra" and strip_accents(phase_raw.lower()) != "otra":
        warnings.append(f"Fase «{phase_raw}» no reconocida; se usa «otra»")
    minutes = parse_number(min_raw)
    messages = parse_number(msg_raw)
    credits = parse_number(cr_raw)
    if credits is None:
        warnings.append("No se ha podido leer la cifra de créditos")
    return {
        "draft": {"title": title, "project": project, "type": typ, "phase": phase,
                  "date": today_local().isoformat(), "minutes": int(round(minutes or 0)),
                  "messages": int(round(messages or 0)), "credits": round(credits or 0, 2),
                  "source": "estimado", "notes": "", "model": model},
        "warnings": warnings,
    }


DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})|(\d{2})/(\d{2})/(\d{4})")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]\.?m\.?)?", re.I)
CRED_RE = re.compile(r"(-?\d[\d.,]*)\s*(?:cr|cré|cred)", re.I)
NUM_RE = re.compile(r"-?\d[\d.,]*")


def _find_col(header: list, keys: tuple) -> Optional[int]:
    for i, h in enumerate(header):
        hn = strip_accents(str(h).strip().lower())
        if any(k in hn for k in keys):
            return i
    return None


def parse_statement_csv(text: str) -> Optional[dict]:
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=",;\t")
    except csv.Error:
        return None
    rows = list(csv.reader(lines, dialect))
    header = rows[0]
    if len(header) < 2:
        return None
    cred_col = _find_col(header, ("credit", "credito", "creditos", "coste", "cost", "amount", "importe", "usage", "uso"))
    date_col = _find_col(header, ("date", "fecha", "day", "dia", "time", "created", "timestamp"))
    if cred_col is None:
        return None
    per_day: dict = {}
    n = 0
    for row in rows[1:]:
        if len(row) <= cred_col:
            continue
        cells = [row[date_col]] if date_col is not None and date_col < len(row) else row
        m = next((DATE_RE.search(c) for c in cells if DATE_RE.search(c)), None)
        if not m:
            continue
        d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m.group(1) else f"{m.group(6)}-{m.group(5)}-{m.group(4)}"
        num = parse_number(row[cred_col])
        if num is None or not valid_date(d):
            continue
        per_day[d] = per_day.get(d, 0.0) + num
        n += 1
    if not per_day:
        return None
    return {"per_day": {k: round(v, 2) for k, v in per_day.items()}, "lines": n, "format": "csv"}


def parse_statement(text: str) -> dict:
    as_csv = parse_statement_csv(text)
    if as_csv:
        return as_csv
    per_day: dict = {}
    lines = 0
    for line in text.splitlines():
        m = DATE_RE.search(line)
        if not m:
            continue
        d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m.group(1) else f"{m.group(6)}-{m.group(5)}-{m.group(4)}"
        if not valid_date(d):
            continue
        rest = TIME_RE.sub(" ", line[:m.start()] + " " + line[m.end():])
        cm = CRED_RE.search(rest)
        if cm:
            num = parse_number(cm.group(1))
        else:
            nums = [x for x in NUM_RE.findall(rest) if any(ch.isdigit() for ch in x)]
            num = parse_number(nums[-1]) if nums else None
        if num is None:
            continue
        per_day[d] = per_day.get(d, 0.0) + num
        lines += 1
    return {"per_day": {k: round(v, 2) for k, v in per_day.items()}, "lines": lines, "format": "text"}


# ---------- budget ----------
def light(pct: Optional[float]) -> str:
    if pct is None:
        return "none"
    if pct < 70:
        return "green"
    if pct <= 100:
        return "amber"
    return "red"


async def budget_status() -> dict:
    settings = await get_settings()
    today = today_local()
    ym = today.strftime("%Y-%m")
    entries = await db.cronos_entries.find({"date": {"$regex": f"^{ym}"}}, {"_id": 0, "credits": 1}).to_list(10000)
    consumed = round(sum(float(e.get("credits") or 0) for e in entries), 2)
    budget = float(settings.get("monthly_budget_credits") or 0)
    price = float(settings.get("price_per_credit_eur") or 0)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    projection = round(consumed / today.day * days_in_month, 2)
    pct = round(consumed / budget * 100, 1) if budget else None
    return {"month": ym, "consumed": consumed, "consumed_eur": round(consumed * price, 2), "budget": budget,
            "budget_eur": round(budget * price, 2), "pct": pct, "remaining": round(budget - consumed, 2),
            "projection": projection, "projection_pct": round(projection / budget * 100, 1) if budget else None,
            "days_elapsed": today.day, "days_in_month": days_in_month, "status": light(pct),
            "alerts_sent": (settings.get("alerts_sent") or {}).get(ym, [])}


def budget_alert_html(th: int, st: dict) -> str:
    link = f'<p><a href="{escape(APP_URL)}" style="color:#00b386">Abrir Cronos</a></p>' if APP_URL.startswith("https://") else ""
    return (f'<table role="presentation" width="100%" style="background:#0d131f;color:#f8fafc"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f'<h2 style="margin:0 0 12px;color:#00ffbf">Presupuesto mensual al {th}%</h2>'
            f'<p>El consumo de créditos de {escape(st["month"])} ha alcanzado el <strong>{st["pct"]}%</strong> del presupuesto.</p>'
            f'<p style="font-family:Courier New,monospace">Consumido: {st["consumed"]} cr ({st["consumed_eur"]} €) / Presupuesto: {st["budget"]} cr<br>'
            f'Proyección fin de mes: {st["projection"]} cr ({st["projection_pct"]}%)</p>{link}'
            f'<p style="font-size:12px;color:#888">Enviado por {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>')


APP_URL = os.environ.get("APP_PUBLIC_URL", "")


async def notify_budget(thresholds: list, st: dict):
    for th in thresholds:
        for to in sorted(admin_emails()):
            try:
                await send_email(to=to, subject=f"[{EMAIL_FROM_NAME}] Presupuesto mensual al {th}%",
                                 html=budget_alert_html(th, st))
            except Exception as e:
                logger.error(f"Aviso de presupuesto no enviado a {to}: {e}")


async def check_budget_alerts(background: Optional[BackgroundTasks] = None) -> dict:
    st = await budget_status()
    if not st["budget"]:
        return st
    settings = await get_settings()
    alerts_sent = settings.get("alerts_sent") or {}
    sent = list(alerts_sent.get(st["month"], []))
    new = [th for th in (80, 100) if st["pct"] >= th and th not in sent]
    if new:
        alerts_sent[st["month"]] = sent + new
        await set_setting("alerts_sent", alerts_sent)
        st["alerts_sent"] = sent + new
        if background is not None:
            background.add_task(notify_budget, new, st)
        else:
            await notify_budget(new, st)
    return st


# ---------- projects ----------
async def projects_overview() -> list:
    projects = await db.cronos_projects.find({}, NO_ID).sort("name", 1).to_list(500)
    ym = today_local().strftime("%Y-%m")
    rows = await db.cronos_entries.find({}, {"_id": 0, "project": 1, "date": 1, "credits": 1}).to_list(20000)
    totals: dict = {}
    for r in rows:
        t = totals.setdefault(r.get("project") or "", {"total": 0.0, "month": 0.0, "count": 0})
        c = float(r.get("credits") or 0)
        t["total"] += c
        t["count"] += 1
        if str(r.get("date", "")).startswith(ym):
            t["month"] += c
    out = []
    for p in projects:
        t = totals.get(p["name"], {"total": 0.0, "month": 0.0, "count": 0})
        mg, tg = p.get("monthly_goal_credits"), p.get("goal_credits")
        pct_month = round(t["month"] / mg * 100, 1) if mg else None
        pct_total = round(t["total"] / tg * 100, 1) if tg else None
        primary = pct_month if mg else pct_total
        out.append({**p, "consumed_total": round(t["total"], 2), "consumed_month": round(t["month"], 2),
                    "entries": t["count"], "pct_month": pct_month, "pct_total": pct_total,
                    "status": light(primary)})
    return out


# ---------- digest ----------
def _fmt(n: float, d: int = 1) -> str:
    return f"{n:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def build_digest() -> dict:
    settings = await get_settings()
    price = float(settings.get("price_per_credit_eur") or 0)
    today = today_local()
    this_monday = today - timedelta(days=today.weekday())
    week_start, week_end = this_monday - timedelta(days=7), this_monday - timedelta(days=1)
    prev_start, prev_end = week_start - timedelta(days=7), week_start - timedelta(days=1)
    week = await fetch_entries({"date": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat()}})
    prev = await fetch_entries({"date": {"$gte": prev_start.isoformat(), "$lte": prev_end.isoformat()}})
    ws, ps = compute_stats(week, price), compute_stats(prev, price)
    budget = await budget_status()
    statement_days = {s["date"] for s in await db.cronos_statements.find({}, NO_ID).to_list(5000)}
    pending = sorted({e["date"] for e in await db.cronos_entries.find({"source": "estimado"}, {"_id": 0, "date": 1}).to_list(20000)
                      if e["date"] not in statement_days}, reverse=True)[:20]
    return {"period": {"from": week_start.isoformat(), "to": week_end.isoformat()},
            "prev_period": {"from": prev_start.isoformat(), "to": prev_end.isoformat()},
            "week": ws, "prev": ps, "top5": ws["top"][:5], "budget": budget, "pending_days": pending}


def digest_html(d: dict) -> str:
    w, p, b = d["week"], d["prev"], d["budget"]

    def row(label, value, prev_value=None):
        delta = ""
        if prev_value is not None:
            delta = f' <span style="color:#94a3b8">(sem. ant. {escape(str(prev_value))})</span>'
        return (f'<tr><td style="padding:6px 10px;color:#94a3b8">{escape(label)}</td>'
                f'<td style="padding:6px 10px;text-align:right;font-family:Courier New,monospace;font-weight:bold">{escape(str(value))}{delta}</td></tr>')

    top_rows = ""
    for t in d["top5"]:
        title, meta_txt = escape(t.get("title") or ""), escape(f'{t.get("project") or ""} · {t.get("type") or ""} · {t.get("phase") or ""}')
        cr = _fmt(float(t.get("credits") or 0))
        top_rows += (f'<tr><td style="padding:4px 10px">{title}<br><span style="color:#64748b;font-size:12px">{meta_txt}</span></td>'
                     f'<td style="padding:4px 10px;text-align:right;font-family:Courier New,monospace">{cr} cr</td></tr>')
    top_rows = top_rows or '<tr><td style="padding:4px 10px;color:#64748b">Sin tareas esta semana</td></tr>'
    pending = ", ".join(d["pending_days"]) if d["pending_days"] else "Ninguno, todo cuadrado"
    link = f'<p><a href="{escape(APP_URL)}" style="color:#00b386">Abrir Cronos</a></p>' if APP_URL.startswith("https://") else ""
    if b["budget"]:
        budget_line = _fmt(b["consumed"]) + " / " + _fmt(b["budget"], 0) + f' cr ({b["pct"]}%) · proyección ' + _fmt(b["projection"]) + " cr"
    else:
        budget_line = "Sin presupuesto configurado"
    rows = (row("Créditos", _fmt(w["credits"]) + " cr", _fmt(p["credits"]) + " cr")
            + row("Coste", _fmt(w["cost_eur"], 2) + " €", _fmt(p["cost_eur"], 2) + " €")
            + row("Horas", _fmt(w["hours"]) + " h", _fmt(p["hours"]) + " h")
            + row("Tareas", w["count"], p["count"])
            + row("Mensajes", w["messages"], p["messages"])
            + row("Corrección vs desarrollo", str(w["comparison"]["correccion_pct"]) + "% corrección"))
    period_from, period_to, month = escape(d["period"]["from"]), escape(d["period"]["to"]), escape(b["month"])
    return (f'<table role="presentation" width="100%" style="max-width:640px;background:#0d131f;color:#f8fafc;border-radius:8px"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f'<h2 style="margin:0 0 4px;color:#00ffbf">Resumen semanal · {period_from} → {period_to}</h2>'
            f'<p style="margin:0 0 16px;color:#94a3b8">{escape(EMAIL_FROM_NAME)} · consumo de agentes IA</p>'
            f'<table width="100%" style="border-collapse:collapse;background:#141c2e;border-radius:6px">{rows}</table>'
            f'<h3 style="margin:20px 0 6px;color:#f8fafc">Top 5 tareas</h3><table width="100%" style="border-collapse:collapse">{top_rows}</table>'
            f'<h3 style="margin:20px 0 6px;color:#f8fafc">Presupuesto {month}</h3><p style="font-family:Courier New,monospace">{budget_line}</p>'
            f'<h3 style="margin:20px 0 6px;color:#f8fafc">Días con entradas estimadas sin cuadrar</h3><p style="font-family:Courier New,monospace;color:#f59e0b">{escape(pending)}</p>'
            f'{link}<p style="font-size:12px;color:#888">Enviado por {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>')


def digest_recipients() -> list:
    env = [e.strip() for e in os.environ.get("WEEKLY_DIGEST_EMAILS", "").split(",") if e.strip()]
    return env or sorted(admin_emails())


async def send_weekly_digest(trigger: str = "manual") -> dict:
    d = await build_digest()
    html = digest_html(d)
    subject = f"[{EMAIL_FROM_NAME}] Resumen semanal {d['period']['from']} → {d['period']['to']}"
    sent, failed = [], []
    for to in digest_recipients():
        try:
            await send_email(to=to, subject=subject, html=html)
            sent.append(to)
        except Exception as e:
            logger.error(f"Resumen semanal no enviado a {to}: {e}")
            failed.append(to)
    await db.audit_log.insert_one({"who": trigger, "action": "weekly_digest", "target": "email",
                                   "detail": f"Enviado a {', '.join(sent) or 'nadie'}", "ip": "", "at": now_iso()})
    return {"sent_to": sent, "failed": failed, "period": d["period"]}


async def run_budget_check():
    await check_budget_alerts(None)


def entry_wiki_markdown(e: dict) -> str:
    rows = [("Proyecto", e.get("project") or "—"), ("Fecha", e.get("date")), ("Tipo", e.get("type")), ("Fase", e.get("phase")),
            ("Usuario", e.get("user") or "—"), ("Modelo IA", e.get("model") or "—"), ("Minutos", e.get("minutes", 0)),
            ("Mensajes", e.get("messages", 0)), ("Créditos", e.get("credits", 0)), ("Origen", e.get("source"))]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return (f"# {e['title']}\n\n## Resumen\nTarea importada del histórico del proyecto **{e.get('project') or '—'}**.\n\n"
            f"| Campo | Valor |\n|---|---|\n{table}\n\n## Notas\n{e.get('notes') or '—'}\n\n"
            "## Qué se ha hecho\n_Pendiente de completar: edita este documento o usa «Documentar con IA» para describir qué se hizo, cómo usarlo y notas técnicas._\n")


async def ensure_wiki_for_entry(e: dict, who: str, source: str = "importado") -> bool:
    if await db.cronos_wiki.find_one({"entry_id": e["id"]}, {"_id": 1}):
        return False
    await db.cronos_wiki.insert_one({
        "id": str(uuid.uuid4()), "title": e["title"], "content": entry_wiki_markdown(e),
        "tags": [t for t in [e.get("type"), e.get("phase"), source] if t], "project": e.get("project") or "",
        "entry_id": e["id"], "source": source, "author": who, "created_at": now_iso(), "updated_at": now_iso(), "history": []})
    return True


# ---------- import ----------
async def import_payload(payload: dict, who: str) -> dict:
    n_e = n_s = n_w = n_auto = 0
    create_wiki = payload.get("create_wiki", True)
    for i, raw in enumerate(payload.get("entries") or []):
        e = {k: raw.get(k) for k in ENTRY_FIELDS}
        e["project"] = e.get("project") or ""
        e["notes"] = e.get("notes") or ""
        e["source"] = e.get("source") or "estimado"
        e["minutes"] = int(e.get("minutes") or 0)
        e["messages"] = int(e.get("messages") or 0)
        e["credits"] = float(e.get("credits") or 0)
        e["user"] = (e.get("user") or who or "").lower()
        e["model"] = e.get("model") or ""
        if not e.get("title") or not e.get("type") or not e.get("phase") or not e.get("date"):
            raise HTTPException(422, f"Entrada #{i + 1}: faltan campos obligatorios (title, type, phase, date)")
        validate_enums(e)
        e["updated_at"] = now_iso()
        eid = raw.get("id") or str(uuid.uuid4())
        await db.cronos_entries.update_one({"id": eid}, {"$set": e, "$setOnInsert": {"id": eid, "created_at": now_iso(), "created_by": who}}, upsert=True)
        await ensure_project(e["project"])
        n_e += 1
        if create_wiki and await ensure_wiki_for_entry({**e, "id": eid}, who):
            n_auto += 1
    for w in payload.get("wiki") or []:
        if not w.get("title"):
            continue
        wid = w.get("id") or str(uuid.uuid4())
        doc = {"title": w["title"], "content": w.get("content") or "", "tags": [str(t) for t in (w.get("tags") or [])],
               "project": w.get("project") or "", "entry_id": w.get("entry_id"), "source": w.get("source") or "importado",
               "updated_at": w.get("updated_at") or now_iso()}
        await db.cronos_wiki.update_one({"id": wid}, {"$set": doc, "$setOnInsert": {
            "id": wid, "author": w.get("author") or who, "created_at": w.get("created_at") or now_iso(), "history": []}}, upsert=True)
        n_w += 1
    for s in payload.get("statements") or []:
        if not valid_date(s.get("date")):
            continue
        await db.cronos_statements.update_one({"date": s["date"]}, {"$set": {
            "date": s["date"], "credits": float(s.get("credits") or 0),
            "imported_at": s.get("imported_at") or now_iso(), "by": s.get("by") or who}}, upsert=True)
        n_s += 1
    return {"entries": n_e, "statements": n_s, "wiki": n_w, "wiki_auto": n_auto}


# ---------- models ----------
class EntryIn(BaseModel):
    title: str = Field(min_length=1)
    project: str = ""
    type: str
    phase: str
    date: str
    minutes: int = Field(ge=0, default=0)
    messages: int = Field(ge=0, default=0)
    credits: float = Field(ge=0, default=0)
    source: str = "estimado"
    notes: str = ""
    estimated_credits: Optional[float] = None
    user: Optional[str] = None
    model: str = ""


class EntryPatch(BaseModel):
    title: Optional[str] = None
    project: Optional[str] = None
    type: Optional[str] = None
    phase: Optional[str] = None
    date: Optional[str] = None
    minutes: Optional[int] = Field(ge=0, default=None)
    messages: Optional[int] = Field(ge=0, default=None)
    credits: Optional[float] = Field(ge=0, default=None)
    source: Optional[str] = None
    notes: Optional[str] = None
    estimated_credits: Optional[float] = None
    user: Optional[str] = None
    model: Optional[str] = None


class LineIn(BaseModel):
    line: str


class TextIn(BaseModel):
    text: str


class DayIn(BaseModel):
    date: str
    credits: float


class ApplyIn(BaseModel):
    days: List[DayIn]


class ImportIn(BaseModel):
    entries: List[dict] = []
    statements: List[dict] = []
    wiki: List[dict] = []
    create_wiki: bool = True


class SettingsIn(BaseModel):
    price_per_credit_eur: Optional[float] = Field(ge=0, default=None)
    monthly_budget_credits: Optional[float] = Field(ge=0, default=None)
    phase_goals: Optional[dict] = None
    models: Optional[List[str]] = None


class ProjectIn(BaseModel):
    name: str = Field(min_length=1)
    monthly_goal_credits: Optional[float] = Field(ge=0, default=None)
    goal_credits: Optional[float] = Field(ge=0, default=None)
    color: Optional[str] = None
    archived: bool = False


class ProjectPatch(BaseModel):
    name: Optional[str] = None
    monthly_goal_credits: Optional[float] = Field(ge=0, default=None)
    goal_credits: Optional[float] = Field(ge=0, default=None)
    color: Optional[str] = None
    archived: Optional[bool] = None


def can_edit(user: dict, doc: dict) -> bool:
    return user["role"] == "admin" or doc.get("user") == user["email"] or doc.get("created_by") == user["email"]


async def workspace_users() -> list:
    emails = {u["email"] for u in await db.users.find({}, {"_id": 0, "email": 1}).to_list(1000)}
    emails |= {u for u in await db.cronos_entries.distinct("user") if u}
    return sorted(emails)


# ---------- routes ----------
@router.get("/meta")
async def meta(user=Depends(get_current_user)):
    names = {p["name"] for p in await db.cronos_projects.find({"archived": {"$ne": True}}, NO_ID).to_list(500)}
    names |= {p for p in await db.cronos_entries.distinct("project") if p}
    settings = await get_settings()
    models = list(settings.get("models") or [])
    models += [m for m in await db.cronos_entries.distinct("model") if m and m not in models]
    return {"types": TYPES, "phases": PHASES, "sources": SOURCES, "projects": sorted(names), "users": await workspace_users(),
            "models": models, "line_format": LINE_FORMAT + " [| modelo]"}


@router.get("/users")
async def users_overview(user=Depends(get_current_user)):
    settings = await get_settings()
    price = float(settings.get("price_per_credit_eur") or 0)
    ym = today_local().strftime("%Y-%m")
    users = {u["email"]: u for u in await db.users.find({}, NO_ID).to_list(1000)}
    entries = await db.cronos_entries.find({}, NO_ID).to_list(20000)
    out: dict = {}
    for email in set(users) | {e.get("user") for e in entries if e.get("user")}:
        u = users.get(email, {})
        out[email] = {"email": email, "name": u.get("name"), "picture": u.get("picture"), "role": role_for(email),
                      "last_login": u.get("last_login"), "count": 0, "credits": 0.0, "minutes": 0, "messages": 0,
                      "credits_month": 0.0, "minutes_month": 0, "last_activity": None, "models": {}}
    for e in entries:
        email = e.get("user")
        if not email or email not in out:
            continue
        o = out[email]
        c = float(e.get("credits") or 0)
        o["count"] += 1
        o["credits"] += c
        o["minutes"] += int(e.get("minutes") or 0)
        o["messages"] += int(e.get("messages") or 0)
        if str(e.get("date", "")).startswith(ym):
            o["credits_month"] += c
            o["minutes_month"] += int(e.get("minutes") or 0)
        if not o["last_activity"] or e["date"] > o["last_activity"]:
            o["last_activity"] = e["date"]
        if e.get("model"):
            o["models"][e["model"]] = o["models"].get(e["model"], 0) + c
    result = []
    for o in out.values():
        o["credits"] = round(o["credits"], 2)
        o["credits_month"] = round(o["credits_month"], 2)
        o["cost_eur"] = round(o["credits"] * price, 2)
        o["hours"] = round(o["minutes"] / 60, 2)
        o["top_model"] = max(o["models"], key=o["models"].get) if o["models"] else None
        o["models"] = [{"model": k, "credits": round(v, 2)} for k, v in sorted(o["models"].items(), key=lambda x: -x[1])]
        result.append(o)
    return sorted(result, key=lambda x: -x["credits"])


@router.get("/entries")
async def list_entries(f: Filters = Depends(), user=Depends(get_current_user)):
    return await fetch_entries(f.query)


@router.post("/entries", status_code=201)
async def create_entry(body: EntryIn, request: Request, background: BackgroundTasks, user=Depends(get_current_user)):
    d = body.model_dump()
    validate_enums(d)
    d["user"] = (d.get("user") or user["email"]).lower() if user["role"] == "admin" else user["email"]
    d.update({"id": str(uuid.uuid4()), "created_by": user["email"], "created_at": now_iso(), "updated_at": now_iso()})
    await db.cronos_entries.insert_one(dict(d))
    await ensure_project(d["project"])
    await audit(user["email"], "entry_create", d["id"], d["title"], request)
    await check_budget_alerts(background)
    return d


@router.patch("/entries/{entry_id}")
async def patch_entry(entry_id: str, body: EntryPatch, request: Request, user=Depends(get_current_user)):
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(400, "No hay cambios")
    doc = await db.cronos_entries.find_one({"id": entry_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Entrada no encontrada")
    if not can_edit(user, doc):
        raise HTTPException(403, "Solo puedes editar tus propias entradas")
    if "user" in changes and user["role"] != "admin":
        changes.pop("user")
    validate_enums(changes)
    if "title" in changes and not changes["title"].strip():
        raise HTTPException(422, "El título no puede estar vacío")
    changes["updated_at"] = now_iso()
    await db.cronos_entries.update_one({"id": entry_id}, {"$set": changes})
    if changes.get("project"):
        await ensure_project(changes["project"])
    await audit(user["email"], "entry_update", entry_id, ", ".join(k for k in changes if k != "updated_at"), request)
    return await db.cronos_entries.find_one({"id": entry_id}, NO_ID)


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, request: Request, user=Depends(get_current_user)):
    doc = await db.cronos_entries.find_one({"id": entry_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Entrada no encontrada")
    if not can_edit(user, doc):
        raise HTTPException(403, "Solo puedes borrar tus propias entradas")
    await db.cronos_entries.delete_one({"id": entry_id})
    await audit(user["email"], "entry_delete", entry_id, doc.get("title", ""), request)
    return {"ok": True}


@router.post("/parse-line")
async def parse_line(body: LineIn, user=Depends(get_current_user)):
    return parse_cronos_line(body.line)


@router.get("/stats")
async def stats(f: Filters = Depends(), user=Depends(get_current_user)):
    settings = await get_settings()
    return compute_stats(await fetch_entries(f.query), float(settings.get("price_per_credit_eur") or 0))


@router.post("/reconcile/preview")
async def reconcile_preview(body: TextIn, user=Depends(get_current_user)):
    parsed = parse_statement(body.text)
    if not parsed["per_day"]:
        raise HTTPException(400, "No se han encontrado líneas con fecha y créditos en el texto pegado")
    days = sorted(parsed["per_day"])
    entries = await fetch_entries({"date": {"$in": days}})
    statements = {s["date"]: s for s in await db.cronos_statements.find({"date": {"$in": days}}, NO_ID).to_list(1000)}
    out = []
    for d in days:
        es = [e for e in entries if e["date"] == d]
        est = round(sum(float(e.get("estimated_credits") if e.get("source") == "confirmado" and e.get("estimated_credits") is not None else e.get("credits") or 0) for e in es), 2)
        real = parsed["per_day"][d]
        out.append({"date": d, "real": real, "estimated": est, "diff": round(real - est, 2),
                    "entries": len(es), "confirmed": sum(1 for e in es if e.get("source") == "confirmado"),
                    "already_imported": d in statements})
    return {"days": out, "lines_parsed": parsed["lines"], "format": parsed.get("format", "text"),
            "totals": {"real": round(sum(x["real"] for x in out), 2), "estimated": round(sum(x["estimated"] for x in out), 2)}}


@router.post("/reconcile/apply")
async def reconcile_apply(body: ApplyIn, request: Request, background: BackgroundTasks, user=Depends(require_admin)):
    adjusted, unassigned, applied = 0, [], []
    for day in body.days:
        if not valid_date(day.date):
            raise HTTPException(422, f"Fecha no válida: {day.date}")
        entries = await db.cronos_entries.find({"date": day.date}, NO_ID).to_list(1000)
        if not entries:
            await db.cronos_entries.insert_one({
                "id": str(uuid.uuid4()), "title": "Sin asignar", "project": "Sin asignar", "type": "desarrollo",
                "phase": "otra", "date": day.date, "minutes": 0, "messages": 0, "credits": round(day.credits, 2),
                "source": "importado", "notes": "Creada automáticamente al cuadrar el extracto (sin tareas ese día)",
                "estimated_credits": None, "created_by": user["email"], "created_at": now_iso(), "updated_at": now_iso()})
            await ensure_project("Sin asignar")
            unassigned.append(day.date)
        else:
            base = [float(e.get("estimated_credits")) if e.get("estimated_credits") is not None else float(e.get("credits") or 0) for e in entries]
            total = sum(base)
            weights = [b / total for b in base] if total > 0 else [1 / len(entries)] * len(entries)
            alloc = [round(day.credits * w, 2) for w in weights]
            alloc[-1] = round(day.credits - sum(alloc[:-1]), 2)
            for e, b, a in zip(entries, base, alloc):
                upd = {"credits": a, "updated_at": now_iso()}
                if e.get("source") != "importado":
                    upd["source"] = "confirmado"
                    upd["estimated_credits"] = b
                await db.cronos_entries.update_one({"id": e["id"]}, {"$set": upd})
            adjusted += len(entries)
        await db.cronos_statements.update_one({"date": day.date}, {"$set": {
            "date": day.date, "credits": round(day.credits, 2), "imported_at": now_iso(), "by": user["email"]}}, upsert=True)
        applied.append(day.date)
    await audit(user["email"], "reconcile_apply", "statements", f"{len(applied)} días, {adjusted} tareas, {len(unassigned)} sin asignar", request)
    await check_budget_alerts(background)
    return {"days_applied": applied, "adjusted_entries": adjusted, "unassigned_days": unassigned}


@router.get("/statements")
async def list_statements(user=Depends(get_current_user)):
    return await db.cronos_statements.find({}, NO_ID).sort("date", -1).to_list(5000)


@router.get("/export.csv")
async def export_csv(f: Filters = Depends(), user=Depends(get_current_user)):
    settings = await get_settings()
    price = float(settings.get("price_per_credit_eur") or 0)
    entries = await fetch_entries(f.query)
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(["fecha", "titulo", "proyecto", "usuario", "modelo", "tipo", "fase", "minutos", "mensajes", "creditos", "coste_eur", "origen", "notas"])
    for e in entries:
        c = float(e.get("credits") or 0)
        w.writerow([e.get("date"), e.get("title"), e.get("project"), e.get("user") or "", e.get("model") or "", e.get("type"), e.get("phase"), e.get("minutes"),
                    e.get("messages"), f"{c:.2f}", f"{c * price:.2f}", e.get("source"), e.get("notes") or ""])
    return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="cronos_{today_local().isoformat()}.csv"'})


@router.post("/import")
async def import_data(body: ImportIn, request: Request, user=Depends(require_admin)):
    res = await import_payload(body.model_dump(), user["email"])
    await audit(user["email"], "import", "entries", f"{res['entries']} entradas, {res['statements']} extractos, {res['wiki']} wiki, {res['wiki_auto']} wiki auto", request)
    return res


@router.post("/wiki/backfill")
async def wiki_backfill(request: Request, project: Optional[str] = None, user=Depends(require_admin)):
    q = {"project": project} if project else {}
    created = 0
    for e in await db.cronos_entries.find(q, NO_ID).to_list(20000):
        if await ensure_wiki_for_entry(e, user["email"]):
            created += 1
    await audit(user["email"], "wiki_backfill", project or "todos", f"{created} documentos creados", request)
    return {"created": created}


@router.get("/settings")
async def read_settings(user=Depends(get_current_user)):
    s = await get_settings()
    return {"price_per_credit_eur": s["price_per_credit_eur"], "monthly_budget_credits": s["monthly_budget_credits"],
            "phase_goals": s.get("phase_goals") or {}, "models": s.get("models") or [],
            "alerts_sent": s.get("alerts_sent") or {}, "digest_recipients": digest_recipients(), "admin_emails": sorted(admin_emails())}


@router.put("/settings")
async def update_settings(body: SettingsIn, request: Request, user=Depends(require_admin)):
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if "phase_goals" in changes:
        goals = {}
        for k, v in changes["phase_goals"].items():
            if k not in PHASES:
                raise HTTPException(422, f"Fase no válida en objetivos: {k}")
            if v is not None and v != "":
                if float(v) < 0:
                    raise HTTPException(422, "El objetivo por fase no puede ser negativo")
                goals[k] = float(v)
        changes["phase_goals"] = goals
    if "models" in changes:
        changes["models"] = [m.strip() for m in dict.fromkeys(changes["models"]) if m and m.strip()]
    for k, v in changes.items():
        await set_setting(k, v)
    await audit(user["email"], "settings_update", "settings", ", ".join(f"{k}={v}" for k, v in changes.items()), request)
    return await read_settings(user)


@router.get("/budget")
async def budget(background: BackgroundTasks, user=Depends(get_current_user)):
    return await check_budget_alerts(background)


@router.get("/projects")
async def list_projects(user=Depends(get_current_user)):
    return await projects_overview()


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn, request: Request, user=Depends(require_admin)):
    if await db.cronos_projects.find_one({"name": body.name}):
        raise HTTPException(409, "Ya existe un proyecto con ese nombre")
    d = {"id": str(uuid.uuid4()), **body.model_dump()}
    await db.cronos_projects.insert_one(dict(d))
    await audit(user["email"], "project_create", d["id"], d["name"], request)
    return d


@router.patch("/projects/{project_id}")
async def patch_project(project_id: str, body: ProjectPatch, request: Request, user=Depends(require_admin)):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No hay cambios")
    old = await db.cronos_projects.find_one({"id": project_id}, NO_ID)
    if not old:
        raise HTTPException(404, "Proyecto no encontrado")
    await db.cronos_projects.update_one({"id": project_id}, {"$set": changes})
    if changes.get("name") and changes["name"] != old["name"]:
        await db.cronos_entries.update_many({"project": old["name"]}, {"$set": {"project": changes["name"]}})
    await audit(user["email"], "project_update", project_id, ", ".join(changes), request)
    return await db.cronos_projects.find_one({"id": project_id}, NO_ID)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, request: Request, user=Depends(require_admin)):
    doc = await db.cronos_projects.find_one({"id": project_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Proyecto no encontrado")
    await db.cronos_projects.delete_one({"id": project_id})
    await audit(user["email"], "project_delete", project_id, doc["name"], request)
    return {"ok": True}


# ---------- sync with other Emergent apps ----------
def mask_source(s: dict) -> dict:
    tok = s.get("token") or ""
    return {**s, "token": (f"…{tok[-4:]}" if tok else ""), "has_token": bool(tok)}


async def fetch_source(src: dict) -> dict:
    base = (src.get("base_url") or "").rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("La URL debe empezar por https://")
    headers = {"Accept": "application/json"}
    if src.get("token"):
        headers["Authorization"] = f"Bearer {src['token']}"
        headers["X-API-Key"] = src["token"]
    payload: dict = {"entries": [], "statements": [], "wiki": []}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(f"{base}/api/cronos/export.json", headers=headers)
        if r.status_code in (401, 403):
            raise ValueError("La app remota ha rechazado la clave de sincronización (401/403). Revisa el token de la fuente")
        if r.status_code == 200 and isinstance(r.json(), dict):
            data = r.json()
            for k in payload:
                payload[k] = data.get(k) or []
            return payload
        r = await c.get(f"{base}/api/cronos/entries", headers=headers)
        if r.status_code in (401, 403):
            raise ValueError("La app remota ha rechazado el token (401/403)")
        if r.status_code == 404:
            raise ValueError("La app remota no expone /api/cronos/export.json ni /api/cronos/entries. Pide a su agente que añada el endpoint de exportación")
        r.raise_for_status()
        payload["entries"] = r.json() if isinstance(r.json(), list) else (r.json().get("items") or [])
        for k in ("statements", "wiki"):
            rr = await c.get(f"{base}/api/cronos/{k}", headers=headers)
            if rr.status_code == 200 and isinstance(rr.json(), list):
                payload[k] = rr.json()
    return payload


async def run_sync(who: str) -> dict:
    settings = await get_settings()
    results = []
    for src in settings.get("sync_sources") or []:
        if not src.get("enabled", True):
            continue
        item = {"name": src.get("name"), "base_url": src.get("base_url")}
        try:
            payload = await fetch_source(src)
            if src.get("project"):
                for e in payload["entries"]:
                    e["project"] = src["project"]
                for w in payload["wiki"]:
                    w["project"] = src["project"]
            for e in payload["entries"]:
                e.setdefault("source", "estimado")
                if not e.get("user"):
                    e["user"] = src.get("default_user") or who
            res = await import_payload(payload, f"sync:{src.get('name') or src.get('base_url')}")
            item.update({"ok": True, **res, "fetched": len(payload["entries"])})
        except Exception as ex:
            logger.error(f"Sync {src.get('name')}: {ex}")
            item.update({"ok": False, "error": str(ex)[:300]})
        results.append(item)
    last = {"at": now_iso(), "by": who, "results": results}
    await set_setting("last_sync", last)
    await db.audit_log.insert_one({"who": who, "action": "sync", "target": "sources", "detail": f"{sum(1 for r in results if r.get('ok'))}/{len(results)} fuentes OK", "ip": "", "at": now_iso()})
    return last


class SyncSourceIn(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=8)
    token: Optional[str] = None
    project: str = ""
    default_user: str = ""
    enabled: bool = True


@router.get("/sync/status")
async def sync_status(user=Depends(get_current_user)):
    s = await get_settings()
    return {"last_sync": s.get("last_sync"), "sources": [mask_source(x) for x in (s.get("sync_sources") or [])]}


@router.post("/sync")
async def sync_now(request: Request, background: BackgroundTasks, user=Depends(require_admin)):
    s = await get_settings()
    if not (s.get("sync_sources") or []):
        raise HTTPException(400, "No hay fuentes de sincronización configuradas. Añádelas en Ajustes → Sincronización")
    res = await run_sync(user["email"])
    await check_budget_alerts(background)
    return res


@router.post("/sync/sources", status_code=201)
async def add_sync_source(body: SyncSourceIn, request: Request, user=Depends(require_admin)):
    s = await get_settings()
    sources = list(s.get("sync_sources") or [])
    d = {"id": str(uuid.uuid4()), **body.model_dump()}
    d["base_url"] = d["base_url"].rstrip("/")
    if not d["base_url"].startswith("https://"):
        raise HTTPException(422, "La URL debe empezar por https://")
    sources.append(d)
    await set_setting("sync_sources", sources)
    await audit(user["email"], "sync_source_add", d["id"], d["name"], request)
    return mask_source(d)


class SyncSourcePatch(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    token: Optional[str] = None
    project: Optional[str] = None
    default_user: Optional[str] = None
    enabled: Optional[bool] = None


@router.patch("/sync/sources/{source_id}")
async def patch_sync_source(source_id: str, body: SyncSourcePatch, request: Request, user=Depends(require_admin)):
    s = await get_settings()
    sources = list(s.get("sync_sources") or [])
    idx = next((i for i, x in enumerate(sources) if x.get("id") == source_id), None)
    if idx is None:
        raise HTTPException(404, "Fuente no encontrada")
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if "base_url" in changes:
        changes["base_url"] = changes["base_url"].rstrip("/")
        if not changes["base_url"].startswith("https://"):
            raise HTTPException(422, "La URL debe empezar por https://")
    sources[idx] = {**sources[idx], **changes}
    await set_setting("sync_sources", sources)
    await audit(user["email"], "sync_source_update", source_id, ", ".join(changes), request)
    return mask_source(sources[idx])


@router.delete("/sync/sources/{source_id}")
async def delete_sync_source(source_id: str, request: Request, user=Depends(require_admin)):
    s = await get_settings()
    sources = [x for x in (s.get("sync_sources") or []) if x.get("id") != source_id]
    if len(sources) == len(s.get("sync_sources") or []):
        raise HTTPException(404, "Fuente no encontrada")
    await set_setting("sync_sources", sources)
    await audit(user["email"], "sync_source_delete", source_id, "", request)
    return {"ok": True}


@router.get("/export.json")
async def export_json(user=Depends(get_current_user)):
    return {"entries": await db.cronos_entries.find({}, NO_ID).to_list(20000),
            "statements": await db.cronos_statements.find({}, NO_ID).to_list(5000),
            "wiki": await db.cronos_wiki.find({}, {"_id": 0, "history": 0}).to_list(2000)}


@router.get("/digest/preview")
async def digest_preview(user=Depends(require_admin)):
    d = await build_digest()
    return {**d, "recipients": digest_recipients(), "html": digest_html(d)}


@router.post("/digest/send")
async def digest_send(request: Request, user=Depends(require_admin)):
    res = await send_weekly_digest(user["email"])
    if not res["sent_to"]:
        raise HTTPException(502, "No se pudo enviar el resumen a ningún destinatario")
    return res


@router.get("/audit")
async def audit_list(user=Depends(require_admin)):
    return await db.audit_log.find({}, NO_ID).sort("at", -1).to_list(50)
