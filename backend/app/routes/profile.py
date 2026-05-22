from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import require_user_id
from app.db.database import get_conn

router = APIRouter()

_MAX_AVATAR_CHARS = 380_000


class ProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    job_title: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=4000)
    avatar_url: str | None = Field(default=None, max_length=_MAX_AVATAR_CHARS)


def _normalize_phone(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if len(s) > 40:
        raise HTTPException(status_code=400, detail="Phone is too long")
    if not re.fullmatch(r"[\d\s\-+().]{6,40}", s):
        raise HTTPException(status_code=400, detail="Phone may only contain digits and common separators")
    return s


def _validate_avatar(url: str | None) -> str | None:
    if url is None:
        return None
    s = url.strip()
    if not s:
        return None
    if len(s) > _MAX_AVATAR_CHARS:
        raise HTTPException(status_code=400, detail="Profile image is too large (try a smaller photo)")
    if not s.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Profile image must be a PNG, JPEG, GIF, or WebP file")
    if ";base64," not in s:
        raise HTTPException(status_code=400, detail="Invalid image data")
    return s


def _row_to_public(row: object) -> dict:
    def g(key: str) -> object:
        return row[key]  # type: ignore[index]

    pc = g("profile_complete")
    if pc is None:
        complete = True
    else:
        complete = bool(int(pc))

    def opt_str(key: str) -> str | None:
        v = g(key)
        if v is None or v == "":
            return None
        return str(v)

    return {
        "id": int(g("id")),
        "name": str(g("name")),
        "email": str(g("email")),
        "phone": opt_str("phone"),
        "job_title": opt_str("job_title"),
        "bio": opt_str("bio"),
        "avatar_url": opt_str("avatar_url"),
        "profile_complete": complete,
    }


@router.get("/profile")
def get_profile(user_id: int = Depends(require_user_id)):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, name, email, phone, job_title, bio, avatar_url, profile_complete
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"profile": _row_to_public(row)}


@router.patch("/profile")
def patch_profile(body: ProfilePatch, user_id: int = Depends(require_user_id)):
    updates: list[str] = []
    values: list[object] = []

    if body.name is not None:
        n = body.name.strip()
        if len(n) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        updates.append("name = ?")
        values.append(n)
    if body.phone is not None:
        updates.append("phone = ?")
        values.append(_normalize_phone(body.phone))
    if body.job_title is not None:
        jt = body.job_title.strip()
        updates.append("job_title = ?")
        values.append(jt or None)
    if body.bio is not None:
        b = body.bio.strip()
        updates.append("bio = ?")
        values.append(b or None)
    if body.avatar_url is not None:
        v = body.avatar_url.strip()
        updates.append("avatar_url = ?")
        values.append(_validate_avatar(v) if v else None)

    if not updates:
        return get_profile(user_id)

    values.append(user_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(values),
        )
        conn.commit()
    return get_profile(user_id)


@router.post("/profile/complete")
def complete_profile(user_id: int = Depends(require_user_id)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT name, profile_complete FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        name = str(row["name"]).strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        conn.execute(
            "UPDATE users SET profile_complete = 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    return {"ok": True, "profile_complete": True, "profile": get_profile(user_id)["profile"]}
