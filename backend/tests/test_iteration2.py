"""Iteration 2: multi-user, model, wiki, instructions tests."""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://cronos-tiempo.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = "test_session_e1"
VIEWER = "test_session_viewer"


def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---- meta ----
class TestMeta:
    def test_meta_has_users_models_line_format(self):
        r = requests.get(f"{API}/cronos/meta", headers=H(ADMIN))
        assert r.status_code == 200
        d = r.json()
        assert "users" in d and isinstance(d["users"], list)
        assert "models" in d and isinstance(d["models"], list)
        assert "[| modelo]" in d["line_format"]


# ---- parse-line ----
class TestParseLine:
    def test_parse_line_with_model(self):
        line = "#cronos | T | dev | p1 | 5 | 1 | 10 | Proy | GPT-5"
        r = requests.post(f"{API}/cronos/parse-line", headers=H(ADMIN), json={"line": line})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["draft"]["model"] == "GPT-5"
        assert d["draft"]["project"] == "Proy"


# ---- entry user/permissions ----
class TestEntryPermissions:
    created_ids = []

    def test_viewer_create_forced_user(self):
        payload = {
            "title": "TEST_viewer_forced",
            "type": "desarrollo",
            "phase": "P1",
            "date": "2026-01-10",
            "minutes": 5,
            "messages": 1,
            "credits": 1,
            "user": "fran.gomez@disruptivos.com",
            "model": "GPT-5",
        }
        r = requests.post(f"{API}/cronos/entries", headers=H(VIEWER), json=payload)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["user"] == "viewer.test@disruptivos.com"
        TestEntryPermissions.created_ids.append(d["id"])

    def test_viewer_patch_own(self):
        eid = TestEntryPermissions.created_ids[0]
        r = requests.patch(f"{API}/cronos/entries/{eid}", headers=H(VIEWER), json={"notes": "owned-edit"})
        assert r.status_code == 200
        assert r.json()["notes"] == "owned-edit"

    def test_viewer_patch_admin_entry_forbidden(self):
        r = requests.patch(f"{API}/cronos/entries/cronos-standalone-prompt", headers=H(VIEWER), json={"notes": "x"})
        assert r.status_code == 403

    def test_viewer_delete_admin_entry_forbidden(self):
        r = requests.delete(f"{API}/cronos/entries/cronos-standalone-prompt", headers=H(VIEWER))
        assert r.status_code == 403

    def test_admin_can_set_user(self):
        payload = {
            "title": "TEST_admin_assign",
            "type": "desarrollo",
            "phase": "P1",
            "date": "2026-01-10",
            "minutes": 5,
            "messages": 1,
            "credits": 1,
            "user": "viewer.test@disruptivos.com",
            "model": "GPT-5",
        }
        r = requests.post(f"{API}/cronos/entries", headers=H(ADMIN), json=payload)
        assert r.status_code == 201
        d = r.json()
        assert d["user"] == "viewer.test@disruptivos.com"
        TestEntryPermissions.created_ids.append(d["id"])
        # admin can patch viewer's entry
        r2 = requests.patch(f"{API}/cronos/entries/{d['id']}", headers=H(ADMIN), json={"notes": "admin-edit"})
        assert r2.status_code == 200
        assert r2.json()["notes"] == "admin-edit"

    def test_zz_cleanup(self):
        for eid in TestEntryPermissions.created_ids:
            r = requests.delete(f"{API}/cronos/entries/{eid}", headers=H(ADMIN))
            assert r.status_code == 200


# ---- /users ----
class TestUsers:
    def test_users_overview(self):
        r = requests.get(f"{API}/cronos/users", headers=H(ADMIN))
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and rows
        row = next((x for x in rows if x["email"] == "fran.gomez@disruptivos.com"), None)
        assert row is not None
        for k in ("email", "role", "count", "credits", "cost_eur", "hours", "credits_month", "top_model", "last_activity"):
            assert k in row, f"missing {k}"


# ---- stats filters ----
class TestStats:
    def test_stats_breakdowns(self):
        r = requests.get(f"{API}/cronos/stats", headers=H(ADMIN))
        assert r.status_code == 200
        d = r.json()
        assert "by_model" in d and "by_user" in d

    def test_stats_filter_user(self):
        r = requests.get(f"{API}/cronos/stats?user=fran.gomez@disruptivos.com", headers=H(ADMIN))
        assert r.status_code == 200

    def test_stats_filter_model(self):
        r = requests.get(f"{API}/cronos/stats?model=GPT-5", headers=H(ADMIN))
        assert r.status_code == 200


# ---- CSV export ----
class TestCSV:
    def test_csv_header(self):
        r = requests.get(f"{API}/cronos/export.csv", headers=H(ADMIN))
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        first = text.splitlines()[0]
        assert first == "fecha,titulo,proyecto,usuario,modelo,tipo,fase,minutos,mensajes,creditos,coste_eur,origen,notas"


# ---- settings models ----
class TestSettingsModels:
    def test_models_dedup_and_restore(self):
        before = requests.get(f"{API}/cronos/settings", headers=H(ADMIN)).json()
        original_models = before["models"]
        r = requests.put(f"{API}/cronos/settings", headers=H(ADMIN), json={"models": ["A", "B", "A"]})
        assert r.status_code == 200
        assert r.json()["models"] == ["A", "B"]
        # viewer forbidden
        rv = requests.put(f"{API}/cronos/settings", headers=H(VIEWER), json={"models": ["X"]})
        assert rv.status_code == 403
        # restore
        rr = requests.put(f"{API}/cronos/settings", headers=H(ADMIN), json={"models": original_models})
        assert rr.status_code == 200
        assert rr.json()["models"] == original_models


# ---- Wiki CRUD ----
class TestWiki:
    created_ids = []
    admin_doc_id = None

    def test_viewer_create(self):
        payload = {"title": "TEST_viewer_doc", "content": "# Hola\n\nContenido viewer.", "tags": ["test"], "project": ""}
        r = requests.post(f"{API}/cronos/wiki", headers=H(VIEWER), json=payload)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["author"] == "viewer.test@disruptivos.com"
        TestWiki.created_ids.append(d["id"])

    def test_list_no_content(self):
        r = requests.get(f"{API}/cronos/wiki", headers=H(ADMIN))
        assert r.status_code == 200
        docs = r.json()
        assert docs
        for d in docs:
            assert "excerpt" in d
            assert "content" not in d

    def test_get_single(self):
        did = TestWiki.created_ids[0]
        r = requests.get(f"{API}/cronos/wiki/{did}", headers=H(ADMIN))
        assert r.status_code == 200
        assert "content" in r.json()

    def test_viewer_patch_own(self):
        did = TestWiki.created_ids[0]
        r = requests.patch(f"{API}/cronos/wiki/{did}", headers=H(VIEWER), json={"content": "# Hola\n\nActualizado."})
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("history", [])) == 1

    def test_admin_patch_viewer_doc(self):
        did = TestWiki.created_ids[0]
        r = requests.patch(f"{API}/cronos/wiki/{did}", headers=H(ADMIN), json={"tags": ["test", "ia"]})
        assert r.status_code == 200

    def test_admin_create_doc(self):
        payload = {"title": "TEST_admin_doc", "content": "# Admin\n\nAdmin content.", "tags": ["admin-test"]}
        r = requests.post(f"{API}/cronos/wiki", headers=H(ADMIN), json=payload)
        assert r.status_code == 201
        TestWiki.admin_doc_id = r.json()["id"]
        TestWiki.created_ids.append(TestWiki.admin_doc_id)

    def test_viewer_patch_admin_doc_forbidden(self):
        r = requests.patch(f"{API}/cronos/wiki/{TestWiki.admin_doc_id}", headers=H(VIEWER), json={"content": "x"})
        assert r.status_code == 403

    def test_search(self):
        r = requests.get(f"{API}/cronos/wiki?q=TEST_viewer", headers=H(ADMIN))
        assert r.status_code == 200
        hits = r.json()
        assert any("TEST_viewer_doc" in d["title"] for d in hits)

    def test_tags(self):
        r = requests.get(f"{API}/cronos/wiki/tags", headers=H(ADMIN))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_viewer_delete_admin_forbidden(self):
        r = requests.delete(f"{API}/cronos/wiki/{TestWiki.admin_doc_id}", headers=H(VIEWER))
        assert r.status_code == 403

    def test_zz_cleanup(self):
        for did in TestWiki.created_ids:
            r = requests.delete(f"{API}/cronos/wiki/{did}", headers=H(ADMIN))
            assert r.status_code == 200


# ---- Wiki AI generate (single call) ----
class TestWikiGenerate:
    def test_generate_empty_body(self):
        r = requests.post(f"{API}/cronos/wiki/generate", headers=H(ADMIN), json={})
        assert r.status_code == 400

    def test_generate_short_description(self):
        r = requests.post(f"{API}/cronos/wiki/generate", headers=H(ADMIN),
                          json={"description": "prueba corta de documentación"},
                          timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("title")
        assert "# " in d.get("content", "")
        assert "ia" in d.get("tags", [])


# ---- Instructions ----
class TestInstructions:
    def test_instructions(self):
        r = requests.get(f"{API}/cronos/instructions", headers=H(ADMIN))
        assert r.status_code == 200
        content = r.json()["content"]
        assert len(content) > 1000
        assert content.startswith("# Cronos")
