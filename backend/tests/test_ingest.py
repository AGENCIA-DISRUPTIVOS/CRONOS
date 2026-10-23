"""Tests de la ingesta por empuje, el registro de apps, la wiki automática y las alertas (iteración 5)."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
ADMIN_TOKEN = os.environ.get("TEST_ADMIN_TOKEN", "local_dev_session")
API = f"{BASE_URL}/api/cronos"


def admin():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def app_token():
    name = f"TEST app {uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/apps", headers=admin(), json={"name": name, "project": name})
    assert r.status_code == 201, r.text
    data = r.json()
    yield {"id": data["id"], "name": name, "token": data["token"], "instructions": data["instructions"]}
    entries = requests.get(f"{API}/entries", headers=admin(), params={"project": name}).json()
    for e in entries:
        requests.delete(f"{API}/entries/{e['id']}", headers=admin())
    requests.delete(f"{API}/apps/{data['id']}", headers=admin())


def push(token, body):
    return requests.post(f"{API}/ingest", headers={"Authorization": f"Bearer {token}"}, json=body)


def entry(**kw):
    base = {"external_id": uuid.uuid4().hex, "title": "Login con Google", "user": "Ana.Lopez@disruptivos.com", "type": "fix", "phase": "P2",
            "minutes": 25, "messages": 4, "credits": 12.5, "tokens_in": 184000, "tokens_out": 9200, "cost_eur": 0.125,
            "model": "Claude Fable 5.1", "summary": "Se ha añadido el login con Google.\n- Endpoint /api/auth/session"}
    base.update(kw)
    return base


def test_create_app_returns_token_once_and_instructions(app_token):
    assert app_token["token"].startswith("crn_")
    ins = app_token["instructions"]
    assert app_token["token"] in ins and "CRONOS_INGEST_URL" in ins and "tokens_estimated" in ins
    listed = requests.get(f"{API}/apps", headers=admin()).json()
    a = next(x for x in listed if x["id"] == app_token["id"])
    assert "token" not in a and "token_hash" not in a and a["token_hint"].startswith("…")


def test_instructions_template_has_placeholder():
    md = requests.get(f"{API}/apps/instructions-template", headers=admin()).json()["markdown"]
    assert "<TOKEN_DE_LA_APP>" in md


def test_ingest_rejects_missing_and_wrong_token():
    assert requests.post(f"{API}/ingest", json={"title": "x"}).status_code == 401
    assert push("crn_malo", {"title": "x"}).status_code == 401
    assert push("sin-prefijo", {"title": "x"}).status_code == 401


def test_ingest_requires_admin_for_apps():
    assert requests.get(f"{API}/apps").status_code == 401


def test_ingest_creates_entry_with_tokens_wiki_and_normalization(app_token):
    e = entry()
    r = push(app_token["token"], {"entries": [e]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["received"] == 1 and body["wiki_created"] == 1 and body["warnings"] == []
    saved = next(x for x in requests.get(f"{API}/entries", headers=admin(), params={"project": app_token["name"]}).json()
                 if x["external_id"] == e["external_id"])
    assert saved["type"] == "corrección" and saved["phase"] == "P2"            # «fix» normalizado
    assert saved["user"] == "ana.lopez@disruptivos.com"                         # en minúsculas
    assert (saved["tokens_in"], saved["tokens_out"], saved["cost_eur"]) == (184000, 9200, 0.125)
    assert saved["channel"] == "push" and saved["app"] == app_token["name"] and saved["project"] == app_token["name"]
    wiki = requests.get(f"{API}/wiki", headers=admin(), params={"entry_id": saved["id"], "full": "true"}).json()
    assert len(wiki) == 1 and wiki[0]["source"] == "push"
    assert "Se ha añadido el login con Google" in wiki[0]["content"] and "184.000 / 9.200" in wiki[0]["content"]


def test_ingest_is_idempotent_and_updates_wiki(app_token):
    e = entry(title="Tarea idempotente")
    assert push(app_token["token"], e).json()["wiki_created"] == 1
    again = push(app_token["token"], {**e, "summary": "Resumen corregido"}).json()
    assert again["wiki_created"] == 0 and again["wiki_updated"] == 1
    items = [x for x in requests.get(f"{API}/entries", headers=admin(), params={"project": app_token["name"]}).json()
             if x["external_id"] == e["external_id"]]
    assert len(items) == 1
    wiki = requests.get(f"{API}/wiki", headers=admin(), params={"entry_id": items[0]["id"], "full": "true"}).json()
    assert len(wiki) == 1 and "Resumen corregido" in wiki[0]["content"]


def test_ingest_without_user_or_external_id_warns_and_does_not_duplicate(app_token):
    e = {"title": "Sin usuario ni id", "credits": 3}
    r1 = push(app_token["token"], e).json()
    r2 = push(app_token["token"], e).json()
    assert r1["ids"] == r2["ids"] and len(r1["warnings"]) == 2
    saved = next(x for x in requests.get(f"{API}/entries", headers=admin(), params={"project": app_token["name"]}).json() if x["id"] == r1["ids"][0])
    assert saved["user"] == "sin asignar"


def test_ingest_validation_errors(app_token):
    assert push(app_token["token"], {"entries": []}).status_code == 422
    assert push(app_token["token"], {"entries": [{"credits": 1}]}).status_code == 422          # falta title
    assert push(app_token["token"], {"entries": [entry(credits=-5)]}).status_code == 422
    assert push(app_token["token"], {"entries": [entry() for _ in range(51)]}).status_code == 422


def test_stats_include_tokens_and_by_app(app_token):
    push(app_token["token"], entry(title="Para estadísticas"))
    st = requests.get(f"{API}/stats", headers=admin(), params={"project": app_token["name"]}).json()
    assert st["tokens_in"] >= 184000 and st["tokens"] == st["tokens_in"] + st["tokens_out"]
    assert any(a["key"] == app_token["name"] for a in st["by_app"])


def test_disabled_app_is_rejected_and_rotation_invalidates_old_token(app_token):
    r = requests.patch(f"{API}/apps/{app_token['id']}", headers=admin(), json={"enabled": False})
    assert r.status_code == 200
    assert push(app_token["token"], entry()).status_code == 403
    requests.patch(f"{API}/apps/{app_token['id']}", headers=admin(), json={"enabled": True})
    rot = requests.post(f"{API}/apps/{app_token['id']}/rotate", headers=admin()).json()
    assert push(app_token["token"], entry()).status_code == 401
    assert push(rot["token"], entry()).status_code == 200
    app_token["token"] = rot["token"]


def test_ingest_log_records_ok_and_failures():
    log = requests.get(f"{API}/ingest/log", headers=admin()).json()
    assert any(l["ok"] for l in log) and any(not l["ok"] and l["detail"] == "token no válido" for l in log)


def test_alerts_check_dry_run_flags_silent_app():
    name = f"TEST callada {uuid.uuid4().hex[:6]}"
    a = requests.post(f"{API}/apps", headers=admin(), json={"name": name}).json()
    try:
        # simula una app creada hace 10 días sin ningún envío
        from pymongo import MongoClient
        from datetime import datetime, timezone, timedelta
        MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "cronos_local")].cronos_apps.update_one(
            {"id": a["id"]}, {"$set": {"created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()}})
        res = requests.post(f"{API}/alerts/check", headers=admin(), params={"dry_run": "true"}).json()
        assert res["dry_run"] is True and name in res["silent"] and res["sent"] == []
        assert res["recipients"]
    finally:
        requests.delete(f"{API}/apps/{a['id']}", headers=admin())
