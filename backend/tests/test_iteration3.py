"""Iteration 3 — Wiki auto-generation on cronos import + backfill.

Tests the bug fix for Central Disruptivos imported entries not getting wiki docs.
Endpoints under test:
  - GET  /api/cronos/wiki (filters: project, entry_id)
  - POST /api/cronos/import (auto-creates wiki docs; `wiki` list; `create_wiki` flag)
  - POST /api/cronos/wiki/backfill (admin only)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_TOKEN = "test_session_e1"
VIEWER_TOKEN = "test_session_viewer"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def viewer():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {VIEWER_TOKEN}", "Content-Type": "application/json"})
    return s


# --- Read filters ---------------------------------------------------------

class TestWikiFilters:
    def test_central_disruptivos_has_11_imported_docs(self, admin):
        r = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"project": "Central Disruptivos"})
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list)
        assert len(docs) == 11, f"expected 11 docs, got {len(docs)}"
        for d in docs:
            assert d.get("source") == "importado", f"doc {d.get('id')} source={d.get('source')}"
            assert d.get("entry_id"), f"doc {d.get('id')} missing entry_id"

    def test_filter_by_entry_id_cronos_standalone_prompt(self, admin):
        r = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"entry_id": "cronos-standalone-prompt"})
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) == 1
        assert docs[0]["title"] == "Cronos: traslado a proyecto independiente (prompt + exportación de datos)"
        assert docs[0]["entry_id"] == "cronos-standalone-prompt"


# --- Import auto-wiki + wiki list idempotency -----------------------------

class TestImportAutoWiki:
    ENTRY_ID = "test-imp-wiki-1"
    DOC_ID = "test-imp-doc-1"

    def test_01_import_entry_auto_creates_wiki(self, admin):
        payload = {"entries": [{
            "id": self.ENTRY_ID, "title": "Import wiki test",
            "project": "Central Disruptivos", "type": "pruebas", "phase": "P7",
            "date": "2026-06-10", "minutes": 1, "messages": 1, "credits": 1
        }]}
        r = admin.post(f"{BASE_URL}/api/cronos/import", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("wiki_auto") == 1, data

        g = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"entry_id": self.ENTRY_ID})
        assert g.status_code == 200
        docs = g.json()
        assert len(docs) == 1
        assert docs[0]["source"] == "importado"
        # stash
        pytest.auto_doc_id = docs[0]["id"]

    def test_02_reimport_no_duplicate(self, admin):
        payload = {"entries": [{
            "id": self.ENTRY_ID, "title": "Import wiki test",
            "project": "Central Disruptivos", "type": "pruebas", "phase": "P7",
            "date": "2026-06-10", "minutes": 1, "messages": 1, "credits": 1
        }]}
        r = admin.post(f"{BASE_URL}/api/cronos/import", json=payload)
        assert r.status_code == 200
        assert r.json().get("wiki_auto") == 0

        g = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"entry_id": self.ENTRY_ID})
        assert len(g.json()) == 1

    def test_03_import_with_wiki_list(self, admin):
        payload = {"entries": [], "wiki": [{
            "id": self.DOC_ID, "title": "Doc importada", "content": "# Doc",
            "tags": ["t"], "project": "Central Disruptivos"
        }]}
        r = admin.post(f"{BASE_URL}/api/cronos/import", json=payload)
        assert r.status_code == 200, r.text
        assert r.json().get("wiki") == 1

        r2 = admin.post(f"{BASE_URL}/api/cronos/import", json=payload)
        assert r2.status_code == 200
        # Idempotent: no duplicate doc created (upsert by id). Counter reflects attempts, not inserts.
        g = admin.get(f"{BASE_URL}/api/cronos/wiki")
        matches = [d for d in g.json() if d.get("id") == self.DOC_ID]
        assert len(matches) == 1, f"expected 1 doc with id={self.DOC_ID}, got {len(matches)}"

    def test_04_create_wiki_false_skips_autodoc(self, admin):
        payload = {
            "create_wiki": False,
            "entries": [{
                "id": "test-imp-nowiki", "title": "No wiki import",
                "project": "Central Disruptivos", "type": "pruebas", "phase": "P7",
                "date": "2026-06-10", "minutes": 1, "messages": 1, "credits": 1
            }]
        }
        r = admin.post(f"{BASE_URL}/api/cronos/import", json=payload)
        assert r.status_code == 200, r.text
        assert r.json().get("wiki_auto") == 0

        g = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"entry_id": "test-imp-nowiki"})
        assert g.status_code == 200
        assert g.json() == []

        # cleanup entry
        d = admin.delete(f"{BASE_URL}/api/cronos/entries/test-imp-nowiki")
        assert d.status_code in (200, 204)

    def test_05_cleanup(self, admin):
        d1 = admin.delete(f"{BASE_URL}/api/cronos/entries/{self.ENTRY_ID}")
        assert d1.status_code in (200, 204)
        d2 = admin.delete(f"{BASE_URL}/api/cronos/wiki/{pytest.auto_doc_id}")
        assert d2.status_code in (200, 204)
        d3 = admin.delete(f"{BASE_URL}/api/cronos/wiki/{self.DOC_ID}")
        assert d3.status_code in (200, 204)
        # Verify gone
        g = admin.get(f"{BASE_URL}/api/cronos/wiki", params={"entry_id": self.ENTRY_ID})
        assert g.json() == []


# --- Backfill -------------------------------------------------------------

class TestBackfill:
    def test_backfill_admin_zero_created(self, admin):
        r = admin.post(f"{BASE_URL}/api/cronos/wiki/backfill", params={"project": "Central Disruptivos"})
        assert r.status_code == 200, r.text
        assert r.json().get("created") == 0

    def test_backfill_viewer_forbidden(self, viewer):
        r = viewer.post(f"{BASE_URL}/api/cronos/wiki/backfill")
        assert r.status_code == 403
