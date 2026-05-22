from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.security import create_token, hash_password, verify_password, verify_token
from app.db.database import get_conn

router = APIRouter()
_log = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class GoogleAuthBody(BaseModel):
    """JWT credential from Google Identity Services (Sign in with Google)."""
    credential: str = Field(..., min_length=20)


@router.post("/register")
def register(payload: RegisterRequest):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (payload.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        pw_hash = hash_password(payload.password)
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO users(name, email, password_hash, created_at, bio, job_title, phone, avatar_url, profile_complete)
            VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 0)
            RETURNING id
            """,
            (payload.name, payload.email, pw_hash, now),
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create user")
        user_id = int(row["id"])
    token = create_token(user_id, payload.email)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": payload.name,
            "email": payload.email,
            "profile_complete": False,
        },
    }


@router.post("/login")
def login(payload: LoginRequest):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash, profile_complete FROM users WHERE email = ?",
            (payload.email,),
        ).fetchone()
    if not row or not verify_password(payload.password, str(row["password_hash"])):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    pc_raw = row["profile_complete"]
    profile_complete = bool(int(pc_raw)) if pc_raw is not None else True
    token = create_token(int(row["id"]), str(row["email"]))
    return {
        "token": token,
        "user": {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "email": str(row["email"]),
            "profile_complete": profile_complete,
        },
    }


@router.post("/google")
def auth_google(payload: GoogleAuthBody):
    """
    Sign in or register using Google.
    Set GOOGLE_OAUTH_CLIENT_ID to your Web client ID (same value as VITE_GOOGLE_CLIENT_ID on the frontend).
    """
    try:
        return _auth_google_impl(payload)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("POST /api/auth/google failed")
        raise HTTPException(
            status_code=503,
            detail="Google sign-in could not finish (database or Google token check failed). See server logs.",
        ) from e


def _auth_google_impl(payload: GoogleAuthBody) -> dict:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=501,
            detail="Google sign-in is not configured (set GOOGLE_OAUTH_CLIENT_ID on the server).",
        )
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified")
    email = str(info.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google account has no email")
    name = str(info.get("name") or email.split("@", 1)[0]).strip()[:120]
    if len(name) < 2:
        name = (name + " User")[:120]

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, profile_complete FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row:
            user_id = int(row["id"])
            display_name = str(row["name"])
            pc_raw = row["profile_complete"]
            profile_complete = bool(int(pc_raw)) if pc_raw is not None else True
        else:
            pw_hash = hash_password(secrets.token_urlsafe(32))
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                """
                INSERT INTO users(name, email, password_hash, created_at, bio, job_title, phone, avatar_url, profile_complete)
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 0)
                RETURNING id
                """,
                (name, email, pw_hash, now),
            )
            ins = cur.fetchone()
            conn.commit()
            if not ins:
                raise HTTPException(status_code=500, detail="Failed to create user")
            user_id = int(ins["id"])
            display_name = name
            profile_complete = False
    token = create_token(user_id, email)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": display_name,
            "email": email,
            "profile_complete": profile_complete,
        },
    }


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user": payload}
