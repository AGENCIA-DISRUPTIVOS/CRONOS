"""Recepción por empuje (push) de tareas desde las apps de Emergent, registro de apps y alertas al responsable.

Cada app registrada tiene su propio token; solo se guarda su hash. El pull diario (`run_sync`) sigue siendo el respaldo.
"""
import os
import re
import hmac
import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timezone, timedelta
from html import escape
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from db import db
from auth import require_admin, audit, admin_emails, client_ip
from emailer import send_email, EMAIL_FROM_NAME
import cronos as cr

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cronos")

TOKEN_PREFIX = "crn_"
MAX_ENTRIES_PER_CALL = 50
SILENT_DAYS = 3          # días sin recibir nada de una app registrada antes de avisar
SILENT_REALERT_DAYS = 3  # cada cuántos días se repite el aviso de una app callada


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def alert_recipients() -> list:
    env = [e.strip().lower() for e in os.environ.get("SYNC_ALERT_EMAILS", "").split(",") if e.strip()]
    return env or sorted(admin_emails())


def public_base(request: Optional[Request] = None) -> str:
    base = os.environ.get("APP_PUBLIC_URL", "").rstrip("/")
    if not base and request is not None:
        base = str(request.base_url).rstrip("/")
    return base


# ---------- instrucciones para pegar en cada app ----------
def build_instructions(base_url: str, app_name: str, project: str, token: str = "<TOKEN_DE_LA_APP>") -> str:
    url = f"{base_url}/api/cronos/ingest" if base_url else "https://<URL_DE_CRONOS>/api/cronos/ingest"
    return f'''# CRONOS REPORTING (mandatory, add to this app's agent instructions)

Language: reply to the user in Spanish (es-ES). The text you send to Cronos (title, summary, notes) is also in Spanish.

This app ("{app_name}", project "{project}") must report to **Cronos**, the team's internal usage tracker, EVERY time you finish
a task that changes the app (code, design, data, config, bug fix, tests). Do it at the end of the task, before your final message.
Pure questions that change nothing do not need a report, but a consultation that cost credits does: report it with type "consulta".

## 1. One-time setup
Create these backend environment variables (never hardcode them, never print them, never commit them):

- `CRONOS_INGEST_URL` = `{url}`
- `CRONOS_APP_TOKEN`  = `{token}`
- `CRONOS_DEFAULT_USER` = email of the person who builds this app, only if you cannot know who sent the prompt
- `CRONOS_EXPORT_TOKEN` = a new random secret (used only by Cronos' daily backup sync, see section 5)

Then create `backend/cronos_report.py` with the helper below and call `report_task(...)` after every task.

```python
import os, uuid, json, datetime, httpx

PENDING = os.path.join(os.path.dirname(__file__), "cronos_pending.jsonl")

def report_task(title, user, type="desarrollo", phase="otra", minutes=0, messages=1, credits=0.0,
                tokens_in=0, tokens_out=0, cost_eur=0.0, tokens_estimated=True, model="", summary="", notes=""):
    """Never raises and never blocks the app. Failed reports are queued and resent with the next one."""
    entry = {{"external_id": str(uuid.uuid4()), "title": title, "user": user or os.environ.get("CRONOS_DEFAULT_USER", ""),
             "type": type, "phase": phase, "date": datetime.date.today().isoformat(), "minutes": minutes,
             "messages": messages, "credits": credits, "tokens_in": tokens_in, "tokens_out": tokens_out,
             "cost_eur": cost_eur, "tokens_estimated": tokens_estimated, "model": model, "summary": summary, "notes": notes}}
    batch = [entry]
    try:
        with open(PENDING, encoding="utf-8") as f:
            batch = [json.loads(l) for l in f if l.strip()] + batch
    except FileNotFoundError:
        pass
    try:
        r = httpx.post(os.environ["CRONOS_INGEST_URL"], json={{"entries": batch[:50]}}, timeout=10,
                       headers={{"Authorization": "Bearer " + os.environ["CRONOS_APP_TOKEN"]}})
        r.raise_for_status()
        rest = batch[50:]
    except Exception:
        rest = batch
    with open(PENDING, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\\n" for x in rest)
    return not rest
```

Add `cronos_pending.jsonl` to `.gitignore`. The first time, send one test report titled "Alta de conexión con Cronos"
and tell the user whether it worked (a success answers `{{"ok": true, ...}}`; a 401 means the token is wrong).

## 2. What to send for each task
| field | what to put |
|---|---|
| `title` | short name of what was done in this task (Spanish) |
| `user` | email of the person who sent the prompt. If the conversation does not reveal it, use `CRONOS_DEFAULT_USER`; never invent one |
| `type` | `desarrollo`, `corrección`, `consulta` or `pruebas` |
| `phase` | `P1`..`P7` if the project plan defines phases, otherwise `otra` |
| `minutes` | wall-clock minutes the task took |
| `messages` | number of user messages exchanged in this task |
| `credits` | credits consumed by this task, as shown by the platform. If not visible, estimate and say so in `notes` |
| `tokens_in` / `tokens_out` | tokens read / generated during this task (see section 3) |
| `cost_eur` | cost of this task in euros (see section 3) |
| `tokens_estimated` | `true` unless the platform showed the exact token figures |
| `model` | the model that did the work (for example "Claude Fable 5.1") |
| `summary` | 3 to 8 lines in Spanish: what was implemented, how to use it, files/endpoints touched, anything left pending. **This becomes the task's wiki page**, so write it for a teammate who has never seen the app |
| `notes` | caveats: estimated figures, partial work, known issues |

## 3. Measuring tokens and cost
Cronos cannot read Emergent's billing, so you report the best figures you can measure:
1. If the platform shows tokens or credits for this task, use those exactly and set `tokens_estimated=false`.
2. Otherwise estimate. `tokens_out` = characters you wrote (messages, code, tool calls) divided by 4. `tokens_in` = characters of
   everything you read in this task (prompt, files opened, tool outputs, context re-read on each step) divided by 4.
   Keep the same method every time so figures are comparable. Set `tokens_estimated=true`.
3. `cost_eur`: the real cost in euros if the platform shows it; otherwise `credits` x 0.01 (the price per credit set in Cronos).
Do not leave tokens at 0 when work was done: an honest estimate is more useful than a blank.

## 4. Rules
- Never put secrets, passwords, API keys or end-customer personal data in any field.
- One report per finished task. If the user asks for several things in one message, send one report per task.
- If the report fails, do not retry in a loop and do not tell the user the app is broken: the helper queues it.
- Keep the Spanish wiki-style `summary` current: if you later fix something from an earlier task, send a new report of type "corrección".

## 5. Backup sync (so nothing is lost if a push fails)
Expose `GET /api/cronos/export.json` in this app, protected with `Authorization: Bearer <CRONOS_EXPORT_TOKEN>` (constant-time
comparison, 401 otherwise), returning `{{"entries": [...], "statements": [], "wiki": []}}` with every task you reported
(same fields as above, plus `external_id`, which must be the same value you pushed). Keep each report in a local collection
`cronos_entries` for this. Tell the user the value of `CRONOS_EXPORT_TOKEN` once in the chat so they can register it in Cronos.
Cronos pulls this endpoint once a day and merges by `external_id`, so pushes and pulls never create duplicates.
'''


# ---------- apps ----------
class AppIn(BaseModel):
    name: str = Field(min_length=1)
    project: str = ""
    notes: str = ""


class AppPatch(BaseModel):
    name: Optional[str] = None
    project: Optional[str] = None
    notes: Optional[str] = None
    enabled: Optional[bool] = None


def parse_iso(s: Optional[str]) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(s) if s else None
        return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def app_status(a: dict, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    last = parse_iso(a.get("last_push_at"))
    ref = last or parse_iso(a.get("created_at")) or now
    silent = bool(a.get("enabled", True)) and (now - ref) > timedelta(days=SILENT_DAYS)
    return {"silent": silent, "days_since_push": (now - last).days if last else None}


def app_out(a: dict) -> dict:
    d = {k: v for k, v in a.items() if k not in ("token_hash", "_id")}
    d["token_hint"] = a.get("token_hint", "")
    d.update(app_status(a))
    return d


async def find_app_by_token(token: str) -> Optional[dict]:
    if not token.startswith(TOKEN_PREFIX):
        return None
    a = await db.cronos_apps.find_one({"token_hash": hash_token(token)}, {"_id": 0})
    return a if a and hmac.compare_digest(a["token_hash"], hash_token(token)) else None


@router.get("/apps")
async def list_apps(user=Depends(require_admin)):
    apps = await db.cronos_apps.find({}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return [app_out(a) for a in apps]


@router.get("/apps/instructions-template")
async def instructions_template(request: Request, user=Depends(require_admin)):
    return {"markdown": build_instructions(public_base(request), "<NOMBRE_DE_LA_APP>", "<PROYECTO>")}


@router.post("/apps", status_code=201)
async def create_app(body: AppIn, request: Request, user=Depends(require_admin)):
    name = body.name.strip()
    if await db.cronos_apps.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}):
        raise HTTPException(409, "Ya existe una app con ese nombre")
    token = new_token()
    a = {"id": str(uuid.uuid4()), "name": name, "project": (body.project or name).strip(), "notes": body.notes, "enabled": True,
         "token_hash": hash_token(token), "token_hint": f"…{token[-4:]}", "created_at": cr.now_iso(), "created_by": user["email"],
         "last_push_at": None, "push_count": 0, "last_push_user": "", "last_silent_alert": None}
    await db.cronos_apps.insert_one(dict(a))
    await cr.ensure_project(a["project"])
    await audit(user["email"], "app_create", a["id"], name, request)
    return {**app_out(a), "token": token, "instructions": build_instructions(public_base(request), a["name"], a["project"], token)}


@router.patch("/apps/{app_id}")
async def patch_app(app_id: str, body: AppPatch, request: Request, user=Depends(require_admin)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nada que actualizar")
    res = await db.cronos_apps.find_one_and_update({"id": app_id}, {"$set": upd}, projection={"_id": 0}, return_document=True)
    if not res:
        raise HTTPException(404, "App no encontrada")
    await audit(user["email"], "app_update", app_id, ", ".join(upd), request)
    return app_out(res)


@router.post("/apps/{app_id}/rotate")
async def rotate_app_token(app_id: str, request: Request, user=Depends(require_admin)):
    token = new_token()
    res = await db.cronos_apps.find_one_and_update({"id": app_id}, {"$set": {"token_hash": hash_token(token), "token_hint": f"…{token[-4:]}"}},
                                                   projection={"_id": 0}, return_document=True)
    if not res:
        raise HTTPException(404, "App no encontrada")
    await audit(user["email"], "app_rotate_token", app_id, res["name"], request)
    return {**app_out(res), "token": token, "instructions": build_instructions(public_base(request), res["name"], res["project"], token)}


@router.delete("/apps/{app_id}")
async def delete_app(app_id: str, request: Request, user=Depends(require_admin)):
    res = await db.cronos_apps.delete_one({"id": app_id})
    if not res.deleted_count:
        raise HTTPException(404, "App no encontrada")
    await audit(user["email"], "app_delete", app_id, "", request)
    return {"ok": True}


# ---------- ingesta ----------
class IngestEntry(BaseModel):
    title: str = Field(min_length=1)
    user: Optional[str] = None
    type: str = "desarrollo"
    phase: str = "otra"
    date: Optional[str] = None
    minutes: float = Field(ge=0, default=0)
    messages: float = Field(ge=0, default=0)
    credits: float = Field(ge=0, default=0)
    tokens_in: float = Field(ge=0, default=0)
    tokens_out: float = Field(ge=0, default=0)
    cost_eur: float = Field(ge=0, default=0)
    tokens_estimated: bool = True
    model: str = ""
    summary: str = ""
    notes: str = ""
    external_id: Optional[str] = None


def bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[7:].strip() if auth.lower().startswith("bearer ") else (request.headers.get("x-api-key") or "").strip()


async def log_ingest(app: Optional[dict], ok: bool, n: int, detail: str, request: Request):
    await db.cronos_ingest_log.insert_one({"at": cr.now_iso(), "app_id": (app or {}).get("id"), "app": (app or {}).get("name", "—"),
                                           "ok": ok, "entries": n, "detail": detail[:300], "ip": client_ip(request)})


def normalize_entry(raw: IngestEntry, app: dict, warnings: list, idx: int) -> dict:
    typ = cr.normalize_type(raw.type)
    if not typ:
        warnings.append(f"#{idx + 1}: tipo «{raw.type}» no reconocido; se usa «desarrollo»")
        typ = "desarrollo"
    phase = cr.normalize_phase(raw.phase)
    date = raw.date if raw.date and cr.valid_date(raw.date) else cr.today_local().isoformat()
    if raw.date and date != raw.date:
        warnings.append(f"#{idx + 1}: fecha no válida; se usa hoy")
    user = (raw.user or "").strip().lower()
    if not user:
        warnings.append(f"#{idx + 1}: sin usuario; queda como «{cr.UNASSIGNED_USER}»")
        user = cr.UNASSIGNED_USER
    elif "@" in user and not user.endswith("@disruptivos.com"):
        warnings.append(f"#{idx + 1}: el usuario {user} no es de @disruptivos.com")
    project = app.get("project") or app["name"]
    ext = (raw.external_id or "").strip()
    if not ext:
        ext = hashlib.sha1(f"{user}|{date}|{raw.title}|{raw.credits}".encode("utf-8")).hexdigest()
        warnings.append(f"#{idx + 1}: sin external_id; se deriva uno (reenviar la misma tarea no la duplica)")
    return {"id": cr.entry_uid(project, ext), "title": raw.title.strip(), "project": project, "type": typ, "phase": phase, "date": date,
            "minutes": int(round(raw.minutes)), "messages": int(round(raw.messages)), "credits": round(raw.credits, 2),
            "tokens_in": int(round(raw.tokens_in)), "tokens_out": int(round(raw.tokens_out)), "cost_eur": round(raw.cost_eur, 4),
            "tokens_estimated": raw.tokens_estimated, "source": "estimado", "notes": raw.notes, "user": user, "model": raw.model,
            "summary": raw.summary, "app": app["name"], "external_id": ext, "channel": "push"}


@router.post("/ingest")
async def ingest(request: Request):
    token = bearer(request)
    app = await find_app_by_token(token) if token else None
    if not app:
        await log_ingest(None, False, 0, "token no válido", request)
        raise HTTPException(401, "Token de app no válido")
    if not app.get("enabled", True):
        await log_ingest(app, False, 0, "app desactivada", request)
        raise HTTPException(403, "App desactivada en Cronos")
    try:
        body = await request.json()
    except Exception:
        await log_ingest(app, False, 0, "JSON no válido", request)
        raise HTTPException(400, "El cuerpo debe ser JSON")
    items = body.get("entries") if isinstance(body, dict) and isinstance(body.get("entries"), list) else [body]
    if not items or len(items) > MAX_ENTRIES_PER_CALL or not all(isinstance(i, dict) for i in items):
        await log_ingest(app, False, 0, f"entradas no válidas ({len(items) if isinstance(items, list) else 0})", request)
        raise HTTPException(422, f"Envía entre 1 y {MAX_ENTRIES_PER_CALL} tareas (objetos JSON)")
    warnings: list = []
    entries = []
    for i, raw in enumerate(items):
        try:
            entries.append(normalize_entry(IngestEntry(**raw), app, warnings, i))
        except Exception as ex:
            await log_ingest(app, False, 0, f"tarea #{i + 1} no válida: {str(ex)[:150]}", request)
            raise HTTPException(422, f"Tarea #{i + 1} no válida: {str(ex)[:300]}")
    who = f"push:{app['name']}"
    res = await cr.import_payload({"entries": entries, "create_wiki": False}, who)
    wiki_new = wiki_updated = 0
    for e in entries:
        doc = await db.cronos_wiki.find_one({"entry_id": e["id"]}, {"_id": 0, "id": 1, "source": 1, "history": 1})
        if not doc:
            wiki_new += int(await cr.ensure_wiki_for_entry(e, who, source="push"))
        elif doc.get("source") == "push" and not doc.get("history"):
            # ficha generada por la propia app y aún sin editar por una persona: se mantiene al día
            await db.cronos_wiki.update_one({"id": doc["id"]}, {"$set": {"title": e["title"], "content": cr.entry_wiki_markdown(e), "updated_at": cr.now_iso()}})
            wiki_updated += 1
    last_user = entries[-1]["user"]
    await db.cronos_apps.update_one({"id": app["id"]}, {"$set": {"last_push_at": cr.now_iso(), "last_push_user": last_user},
                                                         "$inc": {"push_count": len(entries)}})
    await log_ingest(app, True, len(entries), f"{len(warnings)} avisos", request)
    return {"ok": True, "app": app["name"], "project": app.get("project"), "received": len(entries), "wiki_created": wiki_new,
            "wiki_updated": wiki_updated, "ids": [e["id"] for e in entries], "warnings": warnings, "import": res}


@router.get("/ingest/log")
async def ingest_log(limit: int = 100, user=Depends(require_admin)):
    return await db.cronos_ingest_log.find({}, {"_id": 0}).sort("at", -1).to_list(min(max(limit, 1), 500))


@router.get("/cron/log")
async def cron_log(limit: int = 100, user=Depends(require_admin)):
    return await db.cron_log.find({}, {"_id": 0}).sort("at", -1).to_list(min(max(limit, 1), 500))


# ---------- salud de la sincronización y avisos ----------
async def update_sync_health(results: list) -> dict:
    """Guarda la racha de fallos de cada fuente de pull y devuelve las que hay que avisar."""
    settings = await cr.get_settings()
    health = dict(settings.get("sync_health") or {})
    failing = []
    for r in results:
        sid = r.get("id") or r.get("name") or r.get("base_url")
        h = dict(health.get(sid) or {"fail_streak": 0, "last_ok": None, "last_error": ""})
        if r.get("ok"):
            h.update({"fail_streak": 0, "last_ok": cr.now_iso(), "last_error": ""})
        else:
            h["fail_streak"] = int(h.get("fail_streak") or 0) + 1
            h["last_error"] = (r.get("error") or "")[:300]
        health[sid] = h
        # aviso en el primer fallo y después cada 3 días seguidos fallando
        if not r.get("ok") and (h["fail_streak"] == 1 or h["fail_streak"] % 3 == 0):
            failing.append({"name": r.get("name"), "base_url": r.get("base_url"), "streak": h["fail_streak"], "error": h["last_error"],
                            "last_ok": h.get("last_ok")})
    await cr.set_setting("sync_health", health)
    return {"failing": failing}


async def silent_apps_to_alert(now: Optional[datetime] = None) -> list:
    now = now or datetime.now(timezone.utc)
    out = []
    for a in await db.cronos_apps.find({"enabled": {"$ne": False}}, {"_id": 0}).to_list(500):
        if not app_status(a, now)["silent"]:
            continue
        last_alert = parse_iso(a.get("last_silent_alert"))
        if last_alert and (now - last_alert) < timedelta(days=SILENT_REALERT_DAYS):
            continue
        out.append(a)
    return out


def problems_html(failing: list, silent: list) -> str:
    app_url = os.environ.get("APP_PUBLIC_URL", "")
    link = f'<p><a href="{escape(app_url)}" style="color:#00b386">Abrir Cronos</a></p>' if app_url.startswith("https://") else ""
    rows = ""
    if failing:
        rows += '<h3 style="color:#ff9966;margin:16px 0 8px">Fuentes de sincronización que fallan</h3><ul>'
        for f in failing:
            rows += (f'<li><strong>{escape(str(f["name"]))}</strong> ({escape(str(f["base_url"]))}): '
                     f'{f["streak"]} día(s) seguidos fallando. Último OK: {escape(str(f["last_ok"] or "nunca"))}.<br>'
                     f'<span style="font-family:Courier New,monospace;font-size:12px">{escape(str(f["error"])[:200])}</span></li>')
        rows += "</ul>"
    if silent:
        rows += f'<h3 style="color:#ff9966;margin:16px 0 8px">Apps que no envían nada desde hace más de {SILENT_DAYS} días</h3><ul>'
        for a in silent:
            days = app_status(a)["days_since_push"]
            rows += (f'<li><strong>{escape(a["name"])}</strong> (proyecto {escape(a.get("project") or "—")}): '
                     f'{"nunca ha enviado nada" if days is None else f"último envío hace {days} días"}. '
                     'Revisa que tenga pegadas las instrucciones de Cronos y el token.</li>')
        rows += "</ul>"
    return (f'<table role="presentation" width="100%" style="background:#0d131f;color:#f8fafc"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f'<h2 style="margin:0 0 12px;color:#00ffbf">Cronos: la sincronización necesita atención</h2>{rows}{link}'
            f'<p style="font-size:12px;color:#888">Enviado por {escape(EMAIL_FROM_NAME)}.</p></td></tr></table>')


async def run_health_alerts(sync_result: Optional[dict] = None, dry_run: bool = False) -> dict:
    """Avisa por email al responsable si el pull falla o si una app registrada lleva días sin enviar."""
    failing = (await update_sync_health(sync_result.get("results") or []))["failing"] if sync_result else []
    silent = await silent_apps_to_alert()
    out = {"failing": failing, "silent": [a["name"] for a in silent], "recipients": alert_recipients(), "sent": [], "failed": [], "dry_run": dry_run}
    if not (failing or silent) or dry_run:
        return out
    html = problems_html(failing, silent)
    subject = f"[{EMAIL_FROM_NAME}] Atención: {len(failing)} fuente(s) con fallo, {len(silent)} app(s) sin enviar"
    for to in out["recipients"]:
        try:
            await send_email(to=to, subject=subject, html=html)
            out["sent"].append(to)
        except Exception as ex:
            logger.error(f"Aviso de sincronización no enviado a {to}: {ex}")
            out["failed"].append(to)
    if out["sent"]:
        for a in silent:
            await db.cronos_apps.update_one({"id": a["id"]}, {"$set": {"last_silent_alert": cr.now_iso()}})
    await db.audit_log.insert_one({"who": "sistema", "action": "sync_alert", "target": "email", "ip": "", "at": cr.now_iso(),
                                   "detail": f"Enviado a {', '.join(out['sent']) or 'nadie'}: {len(failing)} fuentes, {len(silent)} apps"})
    return out


async def run_sync_with_alerts(who: str) -> dict:
    res = await cr.run_sync(who)
    try:
        await run_health_alerts(res)
    except Exception as ex:
        logger.error(f"Comprobación de salud tras la sincronización: {ex}")
    return res


@router.post("/alerts/check")
async def alerts_check(dry_run: bool = True, user=Depends(require_admin)):
    """Revisa ahora las apps calladas (y el último estado de las fuentes). Por defecto en simulación, sin enviar email."""
    return await run_health_alerts(None, dry_run=dry_run)
