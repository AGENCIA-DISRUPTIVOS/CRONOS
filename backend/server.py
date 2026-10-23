import os
import json
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from db import db, client, ROOT_DIR
from auth import router as auth_router
from cronos import router as cronos_router, import_payload, ensure_defaults, send_weekly_digest, run_budget_check
from wiki import router as wiki_router
from ingest import router as ingest_router, run_sync_with_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_defaults()
    if await db.cronos_entries.count_documents({}) == 0:
        seed = json.loads((ROOT_DIR / "seed_data.json").read_text(encoding="utf-8"))
        res = await import_payload(seed, "seed")
        logger.info(f"Seed importado: {res}")
    yield
    client.close()


app = FastAPI(title="Cronos Disruptivos", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(cronos_router)
app.include_router(wiki_router)
app.include_router(ingest_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


async def log_cron(name: str, outcome: str, run_id: str = "", detail: str = "", request: Request = None):
    """Registro persistente de cada llamada del cron (consultable en /api/cronos/cron/log)."""
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")) if request else ""
    await db.cron_log.insert_one({"at": datetime.now(timezone.utc).isoformat(), "cron": name, "outcome": outcome,
                                  "run_id": run_id or "", "detail": detail[:300], "ip": ip})


async def run_logged(name: str, fn, *args, run_id: str = ""):
    try:
        await fn(*args)
        await log_cron(name, "finished", run_id)
    except Exception as ex:
        logger.error(f"Cron {name} falló: {ex}")
        await log_cron(name, "error", run_id, str(ex))


async def cron_guard(request: Request, name: str = "cron") -> bool:
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], CRON_SECRET):
        await log_cron(name, "unauthorized", detail="secreto ausente o incorrecto", request=request)
        raise HTTPException(status_code=401, detail="No autorizado")
    run_id = request.headers.get("x-webhook-id")
    if not run_id:
        try:
            run_id = (await request.json()).get("run_id")
        except Exception:
            run_id = None
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id}):
            await log_cron(name, "duplicate_skipped", run_id, "run_id ya visto; no se ejecuta", request)
            return False
        await db.cron_runs.insert_one({"run_id": run_id, "at": datetime.now(timezone.utc).isoformat()})
    await log_cron(name, "accepted", run_id or "", request=request)
    return True


@app.post("/api/cron/weekly-digest")
async def cron_weekly_digest(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    if await cron_guard(request, "weekly-digest"):
        background.add_task(run_logged, "weekly-digest", send_weekly_digest, "cron")
    return {"status": "accepted"}


@app.post("/api/cron/budget-check")
async def cron_budget_check(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    if await cron_guard(request, "budget-check"):
        background.add_task(run_logged, "budget-check", run_budget_check)
    return {"status": "accepted"}


@app.post("/api/cron/sync")
async def cron_sync(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    if await cron_guard(request, "sync-sources"):
        background.add_task(run_logged, "sync-sources", run_sync_with_alerts, "cron")
    return {"status": "accepted"}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
