import os
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from db import db

ALLOWED_DOMAIN = "disruptivos.com"
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
COOKIE = "session_token"

router = APIRouter(prefix="/api/auth")


def admin_emails() -> set:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


def role_for(email: str) -> str:
    return "admin" if email.lower() in admin_emails() else "viewer"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


async def audit(who: str, action: str, target: str, detail: str, request: Request):
    await db.audit_log.insert_one({
        "who": who, "action": action, "target": target, "detail": detail,
        "ip": client_ip(request), "at": datetime.now(timezone.utc).isoformat(),
    })


def user_out(u: dict) -> dict:
    return {"user_id": u["user_id"], "email": u["email"], "name": u.get("name"),
            "picture": u.get("picture"), "role": role_for(u["email"])}


class SessionIn(BaseModel):
    session_id: str


@router.post("/session")
async def create_session(body: SessionIn, request: Request, response: Response):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="La sesión de Google no es válida o ha caducado")
    data = r.json()
    email = (data.get("email") or "").lower()
    if not email.endswith("@" + ALLOWED_DOMAIN):
        await audit(email or "desconocido", "login_rejected", "auth", "Dominio no permitido", request)
        raise HTTPException(status_code=403, detail=f"Acceso restringido a cuentas @{ALLOWED_DOMAIN}. Has intentado entrar con {email}.")

    now = datetime.now(timezone.utc)
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "name": data.get("name"), "picture": data.get("picture"), "last_login": now.isoformat()}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({"user_id": user_id, "email": email, "name": data.get("name"),
                                   "picture": data.get("picture"), "created_at": now.isoformat(),
                                   "last_login": now.isoformat()})

    token = data["session_token"]
    await db.user_sessions.insert_one({"user_id": user_id, "session_token": token,
                                       "expires_at": (now + timedelta(days=7)).isoformat(),
                                       "created_at": now.isoformat()})
    response.set_cookie(COOKIE, token, httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 3600)
    await audit(email, "login", "auth", "Inicio de sesión", request)
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user_out(user)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sesión caducada")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user_out(user)


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden realizar esta acción")
    return user


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie(COOKIE, path="/", secure=True, samesite="none")
    return {"ok": True}
