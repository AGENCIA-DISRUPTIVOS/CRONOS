"""Backend tests for the Cronos sync feature (iteration 4)."""
import os
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://cronos-tiempo.preview.emergentagent.com"
ADMIN_TOKEN = os.environ.get("TEST_ADMIN_TOKEN", "test_session_e1")
VIEWER_TOKEN = os.environ.get("TEST_VIEWER_TOKEN", "test_session_viewer")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- export.json ----------
def test_export_json_admin():
    r = requests.get(f"{BASE_URL}/api/cronos/export.json", headers=_h(ADMIN_TOKEN))
    assert r.status_code == 200
    data = r.json()
    assert set(["entries", "statements", "wiki"]).issubset(data.keys())
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) == 19


# ---------- sync status ----------
def test_sync_status_shows_existing_source_masked():
    r = requests.get(f"{BASE_URL}/api/cronos/sync/status", headers=_h(ADMIN_TOKEN))
    assert r.status_code == 200
    data = r.json()
    sources = data.get("sources", [])
    assert any(s["name"] == "Prueba (Cronos mismo)" for s in sources)
    s = next(s for s in sources if s["name"] == "Prueba (Cronos mismo)")
    assert s["has_token"] is True
    assert s["token"].startswith("…")
    assert s["token"].endswith("n_e1")  # masked last 4


def test_sync_status_viewer_allowed():
    r = requests.get(f"{BASE_URL}/api/cronos/sync/status", headers=_h(VIEWER_TOKEN))
    assert r.status_code == 200


# ---------- sync as admin ----------
def test_sync_run_admin_idempotent():
    before = requests.get(f"{BASE_URL}/api/cronos/entries", headers=_h(ADMIN_TOKEN)).json()
    r = requests.post(f"{BASE_URL}/api/cronos/sync", headers=_h(ADMIN_TOKEN))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "at" in data and "by" in data and "results" in data
    results = data["results"]
    assert len(results) >= 1
    first = next(r for r in results if r["name"] == "Prueba (Cronos mismo)")
    assert first["ok"] is True
    assert first["entries"] == 19
    assert first["fetched"] == 19
    after = requests.get(f"{BASE_URL}/api/cronos/entries", headers=_h(ADMIN_TOKEN)).json()
    assert len(after) == len(before), "Sync should be idempotent"


def test_sync_viewer_forbidden():
    r = requests.post(f"{BASE_URL}/api/cronos/sync", headers=_h(VIEWER_TOKEN))
    assert r.status_code == 403


# ---------- source management ----------
def test_add_source_rejects_http():
    r = requests.post(f"{BASE_URL}/api/cronos/sync/sources",
                      headers=_h(ADMIN_TOKEN),
                      json={"name": "Insecure", "base_url": "http://insecure", "token": "x"})
    assert r.status_code == 422


def test_broken_source_lifecycle():
    # Add a valid https but non-cronos source
    r = requests.post(f"{BASE_URL}/api/cronos/sync/sources",
                      headers=_h(ADMIN_TOKEN),
                      json={"name": "Fuente rota", "base_url": "https://example.com", "token": "abc"})
    assert r.status_code == 201, r.text
    created = r.json()
    sid = created["id"]
    assert created["token"].endswith("abc")

    try:
        # Run sync: broken source should fail; existing should still succeed
        r = requests.post(f"{BASE_URL}/api/cronos/sync", headers=_h(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        results = r.json()["results"]
        rota = next(x for x in results if x["name"] == "Fuente rota")
        assert rota["ok"] is False
        assert isinstance(rota.get("error"), str) and len(rota["error"]) > 0
        other = next(x for x in results if x["name"] == "Prueba (Cronos mismo)")
        assert other["ok"] is True
    finally:
        # Delete the broken source
        d = requests.delete(f"{BASE_URL}/api/cronos/sync/sources/{sid}", headers=_h(ADMIN_TOKEN))
        assert d.status_code == 200
        assert d.json() == {"ok": True}
        d2 = requests.delete(f"{BASE_URL}/api/cronos/sync/sources/{sid}", headers=_h(ADMIN_TOKEN))
        assert d2.status_code == 404


# ---------- cron ----------
def test_cron_sync_unauthorized():
    r = requests.post(f"{BASE_URL}/api/cron/sync")
    assert r.status_code == 401


def test_cron_sync_with_secret():
    r = requests.post(f"{BASE_URL}/api/cron/sync",
                      headers={"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": "test-sync-1"})
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}
