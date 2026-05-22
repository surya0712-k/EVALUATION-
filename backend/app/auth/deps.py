from __future__ import annotations

import os

from fastapi import Header, HTTPException

from app.auth.security import verify_token


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "").strip().lower() in {"1", "true", "yes"}


def require_user_id(authorization: str | None = Header(default=None)) -> int:
    """Require a valid Bearer token (used for /api/profile regardless of AUTH_REQUIRED)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def resolve_user_id(authorization: str | None = Header(default=None)) -> int | None:
    """
    When AUTH_REQUIRED is true, returns the signed-in user id or raises 401.
    When false, returns None (anonymous usage; evaluations are not scoped to a user).
    """
    if not auth_required():
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload["sub"])
