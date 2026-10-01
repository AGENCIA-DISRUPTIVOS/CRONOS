"""Comprehensive backend tests for Cronos Disruptivos."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cronos-tiempo.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "test_session_e1"
VIEWER_TOKEN = "test_session_viewer"
CRON_SECRET = "307601fe7a97256d0014ba46598846caa5ccae6217192646"
API = f"{BASE_URL}/api"


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- auth ----------
class TestAuth:
    def test_me_admin(self):
        r = requests.get(f"{API}/auth/me", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "admin"
        assert d["email"] == "fran.gomez@disruptivos.com"

    def test_me_viewer(self):
        r = requests.get(f"{API}/auth/me", headers=H(VIEWER_TOKEN))
        assert r.status_code == 200
        assert r.json()["role"] == "viewer"

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401


# ---------- meta ----------
class TestMeta:
    def test_meta(self):
        r = requests.get(f"{API}/cronos/meta", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        for k in ("types", "phases", "sources", "projects", "line_format"):
            assert k in d
        assert "desarrollo" in d["types"]
        assert "P1" in d["phases"]


# ---------- entries filters ----------
class TestEntriesList:
    def test_list_all(self):
        r = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        entries = r.json()
        assert len(entries) >= 11

    def test_filter_project(self):
        r = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN),
                         params={"project": "Central Disruptivos"})
        assert r.status_code == 200
        for e in r.json():
            assert e["project"] == "Central Disruptivos"

    def test_filter_date_range(self):
        r = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN),
                         params={"date_from": "2026-09-30", "date_to": "2026-09-30"})
        assert r.status_code == 200
        for e in r.json():
            assert e["date"] == "2026-09-30"

    def test_filter_type_phase_source(self):
        for key, val in [("type", "desarrollo"), ("phase", "P1"), ("source", "estimado")]:
            r = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), params={key: val})
            assert r.status_code == 200


# ---------- entries CRUD ----------
class TestEntriesCRUD:
    created_id = None

    def test_viewer_cannot_create(self):
        r = requests.post(f"{API}/cronos/entries", headers=H(VIEWER_TOKEN), json={
            "title": "TEST_viewer", "type": "desarrollo", "phase": "P1", "date": "2026-06-15"
        })
        assert r.status_code == 403

    def test_admin_create(self):
        r = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "TEST_admin_create", "project": "TEST_project", "type": "desarrollo",
            "phase": "P1", "date": "2026-06-15", "minutes": 10, "messages": 2, "credits": 5.0
        })
        assert r.status_code == 201
        d = r.json()
        assert d["title"] == "TEST_admin_create"
        assert "id" in d
        TestEntriesCRUD.created_id = d["id"]
        # verify persistence
        g = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN),
                         params={"project": "TEST_project"})
        assert any(e["id"] == d["id"] for e in g.json())

    def test_invalid_type_422(self):
        r = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "x", "type": "invalid", "phase": "P1", "date": "2026-06-15"
        })
        assert r.status_code == 422

    def test_invalid_date_422(self):
        r = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "x", "type": "desarrollo", "phase": "P1", "date": "not-a-date"
        })
        assert r.status_code == 422

    def test_invalid_phase_422(self):
        r = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "x", "type": "desarrollo", "phase": "P99", "date": "2026-06-15"
        })
        assert r.status_code == 422

    def test_patch_admin(self):
        assert TestEntriesCRUD.created_id
        r = requests.patch(f"{API}/cronos/entries/{TestEntriesCRUD.created_id}",
                           headers=H(ADMIN_TOKEN), json={"title": "TEST_admin_updated"})
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_admin_updated"

    def test_patch_viewer_403(self):
        assert TestEntriesCRUD.created_id
        r = requests.patch(f"{API}/cronos/entries/{TestEntriesCRUD.created_id}",
                           headers=H(VIEWER_TOKEN), json={"title": "nope"})
        assert r.status_code == 403

    def test_patch_404(self):
        r = requests.patch(f"{API}/cronos/entries/nonexistent-id",
                           headers=H(ADMIN_TOKEN), json={"title": "x"})
        assert r.status_code == 404

    def test_delete_viewer_403(self):
        assert TestEntriesCRUD.created_id
        r = requests.delete(f"{API}/cronos/entries/{TestEntriesCRUD.created_id}",
                            headers=H(VIEWER_TOKEN))
        assert r.status_code == 403

    def test_delete_admin(self):
        assert TestEntriesCRUD.created_id
        r = requests.delete(f"{API}/cronos/entries/{TestEntriesCRUD.created_id}",
                            headers=H(ADMIN_TOKEN))
        assert r.status_code == 200

    def test_delete_404(self):
        r = requests.delete(f"{API}/cronos/entries/nonexistent-id",
                            headers=H(ADMIN_TOKEN))
        assert r.status_code == 404


# ---------- parse-line ----------
class TestParseLine:
    def test_parse_valid(self):
        line = "#cronos | Tarea X | correccion | p2 | 30 min | 3 msg | 1.234,5 cr | Proyecto Y"
        r = requests.post(f"{API}/cronos/parse-line", headers=H(ADMIN_TOKEN), json={"line": line})
        assert r.status_code == 200
        d = r.json()["draft"]
        assert d["type"] == "corrección"
        assert d["phase"] == "P2"
        assert d["minutes"] == 30
        assert d["messages"] == 3
        assert d["credits"] == 1234.5
        assert d["project"] == "Proyecto Y"

    def test_missing_prefix_400(self):
        r = requests.post(f"{API}/cronos/parse-line", headers=H(ADMIN_TOKEN),
                          json={"line": "Tarea | desarrollo | p1 | 10 | 1 | 1"})
        assert r.status_code == 400

    def test_too_few_fields_400(self):
        r = requests.post(f"{API}/cronos/parse-line", headers=H(ADMIN_TOKEN),
                          json={"line": "#cronos | a | b | c"})
        assert r.status_code == 400


# ---------- stats ----------
class TestStats:
    def test_stats_shape(self):
        r = requests.get(f"{API}/cronos/stats", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        for k in ("count", "credits", "cost_eur", "minutes", "hours", "messages",
                  "comparison", "by_type", "by_phase", "by_source", "daily", "top"):
            assert k in d
        assert d["cost_eur"] == round(d["credits"] * 0.01, 2)
        assert len(d["top"]) <= 8
        assert "correccion" in d["comparison"] and "desarrollo" in d["comparison"]

    def test_stats_filter(self):
        r = requests.get(f"{API}/cronos/stats", headers=H(ADMIN_TOKEN),
                         params={"type": "desarrollo"})
        assert r.status_code == 200
        for b in r.json()["by_type"]:
            assert b["key"] == "desarrollo"


# ---------- reconcile ----------
class TestReconcile:
    def test_preview(self):
        text = ("2026-10-01 09:12 Agente 640,5 créditos\n"
                "01/10/2026 18:40 otro 52 cr\n"
                "2026-09-29 Agente 40\n")
        r = requests.post(f"{API}/cronos/reconcile/preview", headers=H(ADMIN_TOKEN),
                          json={"text": text})
        assert r.status_code == 200
        d = r.json()
        by = {x["date"]: x for x in d["days"]}
        assert "2026-10-01" in by
        assert by["2026-10-01"]["real"] == 692.5
        assert "2026-09-29" in by
        assert by["2026-09-29"]["real"] == 40

    def test_preview_no_dates_400(self):
        r = requests.post(f"{API}/cronos/reconcile/preview", headers=H(ADMIN_TOKEN),
                          json={"text": "no dates here"})
        assert r.status_code == 400

    def test_apply_viewer_403(self):
        r = requests.post(f"{API}/cronos/reconcile/apply", headers=H(VIEWER_TOKEN),
                          json={"days": [{"date": "2026-06-15", "credits": 10}]})
        assert r.status_code == 403

    def test_apply_unassigned(self):
        # Use a day that has no entries
        r = requests.post(f"{API}/cronos/reconcile/apply", headers=H(ADMIN_TOKEN),
                          json={"days": [{"date": "2026-05-20", "credits": 40}]})
        assert r.status_code == 200
        d = r.json()
        assert "2026-05-20" in d["unassigned_days"]
        # Verify 'Sin asignar' entry created
        g = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN),
                         params={"date_from": "2026-05-20", "date_to": "2026-05-20"})
        es = g.json()
        assert any(e.get("title") == "Sin asignar" and e.get("source") == "importado" for e in es)
        # Verify statement created
        s = requests.get(f"{API}/cronos/statements", headers=H(ADMIN_TOKEN))
        assert any(x["date"] == "2026-05-20" for x in s.json())
        # Cleanup
        for e in es:
            if e.get("title") == "Sin asignar":
                requests.delete(f"{API}/cronos/entries/{e['id']}", headers=H(ADMIN_TOKEN))

    def test_apply_proportional(self):
        # Use isolated date to avoid races with other tests
        test_date = "2026-07-20"
        c1 = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "TEST_rec_a", "type": "desarrollo", "phase": "P1",
            "date": test_date, "credits": 30
        })
        c2 = requests.post(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN), json={
            "title": "TEST_rec_b", "type": "desarrollo", "phase": "P1",
            "date": test_date, "credits": 10
        })
        assert c1.status_code == 201 and c2.status_code == 201
        id1, id2 = c1.json()["id"], c2.json()["id"]
        try:
            r = requests.post(f"{API}/cronos/reconcile/apply", headers=H(ADMIN_TOKEN),
                              json={"days": [{"date": test_date, "credits": 100}]})
            assert r.status_code == 200
            g = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN),
                             params={"date_from": test_date, "date_to": test_date})
            es = {e["id"]: e for e in g.json()}
            assert es[id1]["credits"] == 75
            assert es[id2]["credits"] == 25
            assert es[id1]["source"] == "confirmado"
            assert es[id1]["estimated_credits"] == 30
            assert es[id2]["estimated_credits"] == 10
        finally:
            requests.delete(f"{API}/cronos/entries/{id1}", headers=H(ADMIN_TOKEN))
            requests.delete(f"{API}/cronos/entries/{id2}", headers=H(ADMIN_TOKEN))


# ---------- export CSV ----------
class TestExport:
    def test_csv(self):
        r = requests.get(f"{API}/cronos/export.csv", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        text = r.content.decode("utf-8")
        assert text.startswith("\ufeff")
        header_line = text.split("\n")[0].strip("\ufeff\r")
        assert header_line == "fecha,titulo,proyecto,tipo,fase,minutos,mensajes,creditos,coste_eur,origen,notas"


# ---------- import ----------
class TestImport:
    def test_idempotent(self):
        payload = {"entries": [{
            "id": "test-import-1", "title": "Import test", "project": "Central Disruptivos",
            "type": "pruebas", "phase": "P7", "date": "2026-06-10",
            "minutes": 5, "messages": 1, "credits": 2.5, "source": "estimado"
        }], "statements": []}
        r1 = requests.post(f"{API}/cronos/import", headers=H(ADMIN_TOKEN), json=payload)
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/cronos/import", headers=H(ADMIN_TOKEN), json=payload)
        assert r2.status_code == 200
        # ensure only one entry exists with that id
        g = requests.get(f"{API}/cronos/entries", headers=H(ADMIN_TOKEN))
        matches = [e for e in g.json() if e.get("id") == "test-import-1"]
        assert len(matches) == 1
        # cleanup
        requests.delete(f"{API}/cronos/entries/test-import-1", headers=H(ADMIN_TOKEN))


# ---------- settings & budget ----------
class TestSettings:
    def test_get(self):
        r = requests.get(f"{API}/cronos/settings", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        assert "price_per_credit_eur" in d
        assert "monthly_budget_credits" in d

    def test_put_viewer_403(self):
        r = requests.put(f"{API}/cronos/settings", headers=H(VIEWER_TOKEN),
                         json={"price_per_credit_eur": 0.01})
        assert r.status_code == 403

    def test_put_admin(self):
        r = requests.put(f"{API}/cronos/settings", headers=H(ADMIN_TOKEN),
                         json={"price_per_credit_eur": 0.01, "monthly_budget_credits": 5000})
        assert r.status_code == 200
        assert r.json()["price_per_credit_eur"] == 0.01

    def test_budget(self):
        r = requests.get(f"{API}/cronos/budget", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        d = r.json()
        for k in ("month", "consumed", "budget", "pct", "projection", "status"):
            assert k in d


# ---------- projects ----------
class TestProjects:
    created_id = None

    def test_create_duplicate_409(self):
        # First create a test project
        r = requests.post(f"{API}/cronos/projects", headers=H(ADMIN_TOKEN),
                          json={"name": "TEST_project_dup"})
        assert r.status_code == 201
        TestProjects.created_id = r.json()["id"]
        # Try duplicate
        r2 = requests.post(f"{API}/cronos/projects", headers=H(ADMIN_TOKEN),
                           json={"name": "TEST_project_dup"})
        assert r2.status_code == 409

    def test_patch_goal(self):
        assert TestProjects.created_id
        r = requests.patch(f"{API}/cronos/projects/{TestProjects.created_id}",
                           headers=H(ADMIN_TOKEN), json={"monthly_goal_credits": 500})
        assert r.status_code == 200
        assert r.json()["monthly_goal_credits"] == 500

    def test_overview(self):
        r = requests.get(f"{API}/cronos/projects", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        for p in r.json():
            assert "consumed_total" in p and "consumed_month" in p
            assert "status" in p
            assert p["status"] in ("green", "amber", "red", "none")

    def test_delete(self):
        assert TestProjects.created_id
        r = requests.delete(f"{API}/cronos/projects/{TestProjects.created_id}",
                            headers=H(ADMIN_TOKEN))
        assert r.status_code == 200


# ---------- audit ----------
class TestAudit:
    def test_audit_admin(self):
        r = requests.get(f"{API}/cronos/audit", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_audit_viewer_403(self):
        r = requests.get(f"{API}/cronos/audit", headers=H(VIEWER_TOKEN))
        assert r.status_code == 403


# ---------- cron ----------
class TestCron:
    def test_budget_check_no_auth(self):
        r = requests.post(f"{API}/cron/budget-check")
        assert r.status_code == 401

    def test_budget_check_wrong_secret(self):
        r = requests.post(f"{API}/cron/budget-check",
                          headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_budget_check_ok(self):
        r = requests.post(f"{API}/cron/budget-check",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"})
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"
