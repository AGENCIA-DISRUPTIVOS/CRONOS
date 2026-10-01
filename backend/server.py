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


@app.get("/api/health")
async def health():
    return {"status": "ok"}


async def cron_guard(request: Request) -> bool:
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], CRON_SECRET):
        raise HTTPException(status_code=401, detail="No autorizado")
    run_id = request.headers.get("x-webhook-id")
    if not run_id:
        try:
            run_id = (await request.json()).get("run_id")
        except Exception:
            run_id = None
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id}):
            return False
        await db.cron_runs.insert_one({"run_id": run_id, "at": datetime.now(timezone.utc).isoformat()})
    return True


@app.post("/api/cron/weekly-digest")
async def cron_weekly_digest(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    if await cron_guard(request):
        background.add_task(send_weekly_digest, "cron")
    return {"status": "accepted"}


@app.post("/api/cron/budget-check")
async def cron_budget_check(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    if await cron_guard(request):
        background.add_task(run_budget_check)
    return {"status": "accepted"}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
