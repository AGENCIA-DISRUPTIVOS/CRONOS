import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage
from db import db
from auth import get_current_user, audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cronos")
NO_ID = {"_id": 0}
LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
INSTRUCTIONS_PATH = Path(__file__).parent.parent / "instrucciones.md"
SOURCES = ["manual", "agente", "ia", "importado"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def can_edit(user: dict, doc: dict) -> bool:
    return user["role"] == "admin" or doc.get("author") == user["email"]


class WikiIn(BaseModel):
    title: str = Field(min_length=1)
    content: str = ""
    tags: List[str] = []
    project: str = ""
    entry_id: Optional[str] = None
    source: str = "manual"


class WikiPatch(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    project: Optional[str] = None
    entry_id: Optional[str] = None


class GenerateIn(BaseModel):
    entry_id: Optional[str] = None
    description: str = ""
    title: str = ""


@router.get("/wiki")
async def list_wiki(q: Optional[str] = None, project: Optional[str] = None, tag: Optional[str] = None, entry_id: Optional[str] = None, user=Depends(get_current_user)):
    query: dict = {}
    if project:
        query["project"] = project
    if tag:
        query["tags"] = tag
    if entry_id:
        query["entry_id"] = entry_id
    if q:
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"content": {"$regex": q, "$options": "i"}}, {"tags": {"$regex": q, "$options": "i"}}]
    docs = await db.cronos_wiki.find(query, NO_ID).sort("updated_at", -1).to_list(500)
    for d in docs:
        d["excerpt"] = (d.get("content") or "")[:220]
        d.pop("content", None)
    return docs


@router.get("/wiki/tags")
async def wiki_tags(user=Depends(get_current_user)):
    return sorted(t for t in await db.cronos_wiki.distinct("tags") if t)


@router.get("/wiki/{doc_id}")
async def get_wiki(doc_id: str, user=Depends(get_current_user)):
    doc = await db.cronos_wiki.find_one({"id": doc_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    return doc


@router.post("/wiki", status_code=201)
async def create_wiki(body: WikiIn, request: Request, user=Depends(get_current_user)):
    d = body.model_dump()
    d["tags"] = [t.strip() for t in d["tags"] if t.strip()]
    if d["source"] not in SOURCES:
        d["source"] = "manual"
    d.update({"id": str(uuid.uuid4()), "author": user["email"], "created_at": now_iso(), "updated_at": now_iso(), "history": []})
    await db.cronos_wiki.insert_one(dict(d))
    await audit(user["email"], "wiki_create", d["id"], d["title"], request)
    d.pop("history", None)
    return d


@router.patch("/wiki/{doc_id}")
async def patch_wiki(doc_id: str, body: WikiPatch, request: Request, user=Depends(get_current_user)):
    doc = await db.cronos_wiki.find_one({"id": doc_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    if not can_edit(user, doc):
        raise HTTPException(403, "Solo puedes editar tus propios documentos")
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(400, "No hay cambios")
    if "tags" in changes:
        changes["tags"] = [t.strip() for t in changes["tags"] if t.strip()]
    changes["updated_at"] = now_iso()
    changes["updated_by"] = user["email"]
    history_item = {"at": now_iso(), "by": user["email"], "title": doc.get("title"), "content": doc.get("content")}
    await db.cronos_wiki.update_one({"id": doc_id}, {"$set": changes, "$push": {"history": {"$each": [history_item], "$slice": -10}}})
    await audit(user["email"], "wiki_update", doc_id, ", ".join(k for k in changes if k not in ("updated_at", "updated_by")), request)
    return await db.cronos_wiki.find_one({"id": doc_id}, NO_ID)


@router.delete("/wiki/{doc_id}")
async def delete_wiki(doc_id: str, request: Request, user=Depends(get_current_user)):
    doc = await db.cronos_wiki.find_one({"id": doc_id}, NO_ID)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    if not can_edit(user, doc):
        raise HTTPException(403, "Solo puedes borrar tus propios documentos")
    await db.cronos_wiki.delete_one({"id": doc_id})
    await audit(user["email"], "wiki_delete", doc_id, doc.get("title", ""), request)
    return {"ok": True}


SYSTEM_PROMPT = (
    "Eres el documentador técnico de Cronos Disruptivos, la app interna de la agencia Disruptivos para controlar el "
    "consumo de agentes de IA. Escribes en español (es-ES), en Markdown, de forma clara y concisa para el equipo. "
    "Devuelve SOLO el documento Markdown, sin explicaciones previas. Estructura obligatoria: "
    "un título H1, luego secciones H2: 'Resumen', 'Qué se ha hecho', 'Cómo usarlo', 'Notas técnicas' y 'Pendientes / siguientes pasos'. "
    "Si falta información, indica claramente qué habría que completar en lugar de inventarla."
)


@router.post("/wiki/generate")
async def generate_wiki(body: GenerateIn, request: Request, user=Depends(get_current_user)):
    context = []
    entry = None
    if body.entry_id:
        entry = await db.cronos_entries.find_one({"id": body.entry_id}, NO_ID)
        if not entry:
            raise HTTPException(404, "Tarea no encontrada")
        context.append(
            f"Tarea registrada: «{entry['title']}» · proyecto {entry.get('project') or '—'} · tipo {entry['type']} · fase {entry['phase']} · "
            f"fecha {entry['date']} · {entry.get('minutes', 0)} min · {entry.get('messages', 0)} mensajes · {entry.get('credits', 0)} créditos · "
            f"modelo {entry.get('model') or 'desconocido'} · usuario {entry.get('user') or '—'}. Notas: {entry.get('notes') or 'ninguna'}"
        )
    if body.description.strip():
        context.append(f"Descripción del usuario: {body.description.strip()}")
    if not context:
        raise HTTPException(400, "Indica una tarea o una descripción para generar la documentación")
    if body.title.strip():
        context.append(f"Título sugerido: {body.title.strip()}")
    chat = LlmChat(api_key=LLM_KEY, session_id=f"wiki-{uuid.uuid4().hex[:8]}", system_message=SYSTEM_PROMPT).with_model("anthropic", "claude-sonnet-5-5")
    try:
        text = await chat.send_message(UserMessage(text="Documenta esta iteración:\n\n" + "\n\n".join(context)))
    except Exception as e:
        logger.error(f"Generación IA fallida: {e}")
        raise HTTPException(502, "No se pudo generar la documentación con IA")
    text = (text or "").strip()
    title = body.title.strip() or (entry["title"] if entry else "")
    for line in text.splitlines():
        if line.startswith("# "):
            title = title or line[2:].strip()
            break
    tags = [t for t in [entry.get("type") if entry else None, entry.get("phase") if entry else None, "ia"] if t]
    await audit(user["email"], "wiki_generate", body.entry_id or "descripcion", title, request)
    return {"title": title or "Documentación", "content": text, "tags": tags, "project": entry.get("project", "") if entry else "",
            "entry_id": body.entry_id, "model_used": "claude-sonnet-5-5"}


@router.get("/instructions")
async def instructions(user=Depends(get_current_user)):
    if not INSTRUCTIONS_PATH.exists():
        return {"content": "# Instrucciones\n\nTodavía no hay instrucciones.", "updated_at": None}
    return {"content": INSTRUCTIONS_PATH.read_text(encoding="utf-8"),
            "updated_at": datetime.fromtimestamp(INSTRUCTIONS_PATH.stat().st_mtime, tz=timezone.utc).isoformat()}
