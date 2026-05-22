from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import resolve_user_id
from app.db.database import get_conn
from app.graph.workflow import build_workflow

router = APIRouter()
workflow = build_workflow()


def _json_dump(obj: object) -> str:
    return json.dumps(obj if obj is not None else {}, default=str)


def _name_from_linkedin_profile_url(url: str) -> str:
    """Turn /in/slug (optionally with trailing numeric id) into a readable label."""
    try:
        path = (url or "").strip().split("?")[0].rstrip("/")
        slug = path.split("/")[-1]
        if not slug or slug.lower() in {"in", "pub", "company", "school"}:
            return ""
        slug = re.sub(r"-\d{6,}$", "", slug, flags=re.I)
        parts: List[str] = []
        for piece in slug.replace("-", " ").split():
            if piece.isdigit():
                continue
            if len(piece) <= 1:
                continue
            parts.append(piece.capitalize())
        return " ".join(parts).strip()
    except Exception:
        return ""


def _derive_candidate_display_name(
    *,
    linkedin_data: dict,
    github_data: dict,
    linkedin_url: str,
) -> str:
    linkedin_name = str(linkedin_data.get("full_name") or "").strip()
    github_name = str((github_data.get("profile") or {}).get("name") or "").strip()
    slug_name = _name_from_linkedin_profile_url(linkedin_url)
    slug_from_collector = _name_from_linkedin_profile_url(str(linkedin_data.get("linkedin_url") or ""))
    return (
        linkedin_name
        or github_name
        or slug_name
        or slug_from_collector
        or ""
    )


class DeleteReportsBody(BaseModel):
    ids: List[int] = Field(..., min_length=1)


class EvaluateRequest(BaseModel):
    candidate_name: Optional[str] = Field(default=None)
    github_url: str = Field(..., examples=["https://github.com/octocat"])
    linkedin_url: str = Field(..., examples=["https://www.linkedin.com/in/sample-user"])
    target_role: str = Field(default="Software Engineer")
    is_intern: bool = Field(default=False)
    linkedin_experience_years: Optional[float] = Field(
        default=None,
        description="Optional: total years (incl. internships) when LinkedIn is not auto-fetched.",
    )
    linkedin_achievements: Optional[List[str]] = Field(
        default=None,
        description="Optional: role highlights (internships, full-time), one string per item.",
    )
    linkedin_skills: Optional[List[str]] = Field(
        default=None,
        description="Optional: skills if LinkedIn is not auto-fetched.",
    )


@router.post("/evaluate")
def evaluate_profile(payload: EvaluateRequest, user_id: int | None = Depends(resolve_user_id)):
    result = workflow.invoke(payload.model_dump(exclude_none=True))
    output = result.get("output", {})
    github_data = result.get("github_data", {}) or {}
    linkedin_data = result.get("linkedin_data", {}) or {}

    auto_name = _derive_candidate_display_name(
        linkedin_data=linkedin_data,
        github_data=github_data,
        linkedin_url=payload.linkedin_url.strip(),
    )
    final_name = (payload.candidate_name or "").strip() or auto_name or "Unknown Candidate"
    pipeline_snapshot = {
        "processed_features": result.get("processed_features") or {},
        "llm_analysis": result.get("llm_analysis") or {},
        "scoring": result.get("scoring") or {},
        "warnings": result.get("warnings") or [],
    }
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO evaluations (
                candidate_name, github_url, linkedin_url, target_role, is_intern,
                final_score, data_completeness, output_json, created_at,
                github_data_json, linkedin_data_json, pipeline_json, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                final_name,
                payload.github_url.strip(),
                payload.linkedin_url.strip(),
                payload.target_role.strip() or "Software Engineer",
                1 if payload.is_intern else 0,
                float(output.get("final_score", 0.0) or 0.0),
                float(output.get("data_completeness", 0.0) or 0.0),
                _json_dump(output),
                datetime.now(timezone.utc).isoformat(),
                _json_dump(github_data),
                _json_dump(linkedin_data),
                _json_dump(pipeline_snapshot),
                user_id,
            ),
        )
        conn.commit()
    return output


def _parse_json_col(raw: object) -> dict:
    if raw is None or raw == "":
        return {}
    try:
        out = json.loads(str(raw))
        return out if isinstance(out, dict) else {}
    except json.JSONDecodeError:
        return {}


@router.get("/reports")
def list_reports(
    limit: int = 50,
    include_snapshots: bool = False,
    user_id: int | None = Depends(resolve_user_id),
):
    n = max(1, min(200, int(limit)))
    with get_conn() as conn:
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT id, candidate_name, github_url, linkedin_url, target_role, is_intern,
                       final_score, data_completeness, output_json, created_at,
                       github_data_json, linkedin_data_json, pipeline_json, user_id
                FROM evaluations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, n),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, candidate_name, github_url, linkedin_url, target_role, is_intern,
                       final_score, data_completeness, output_json, created_at,
                       github_data_json, linkedin_data_json, pipeline_json, user_id
                FROM evaluations
                ORDER BY id DESC
                LIMIT ?
                """,
                (n,),
            ).fetchall()
    out = []
    for r in rows:
        output_json = _parse_json_col(r["output_json"])
        item: dict = {
            "id": int(r["id"]),
            "candidate_name": str(r["candidate_name"]),
            "github_url": str(r["github_url"]),
            "linkedin_url": str(r["linkedin_url"]),
            "target_role": str(r["target_role"]),
            "is_intern": bool(r["is_intern"]),
            "final_score": float(r["final_score"]),
            "data_completeness": float(r["data_completeness"]),
            "created_at": str(r["created_at"]),
            "report": output_json,
        }
        if include_snapshots:
            item["github_data"] = _parse_json_col(r["github_data_json"])
            item["linkedin_data"] = _parse_json_col(r["linkedin_data_json"])
            item["pipeline"] = _parse_json_col(r["pipeline_json"])
        out.append(item)
    return {"items": out}


@router.post("/reports/delete")
def delete_reports(body: DeleteReportsBody, user_id: int | None = Depends(resolve_user_id)):
    """Bulk delete (POST avoids proxies/CDNs that block DELETE and wrong /api/api URLs)."""
    deleted: List[int] = []
    missing: List[int] = []
    with get_conn() as conn:
        for rid in body.ids:
            rid = int(rid)
            if user_id is not None:
                own = conn.execute(
                    "SELECT 1 FROM evaluations WHERE id = ? AND user_id = ?",
                    (rid, user_id),
                ).fetchone()
            else:
                own = conn.execute("SELECT 1 FROM evaluations WHERE id = ?", (rid,)).fetchone()
            if not own:
                missing.append(rid)
                continue
            conn.execute("DELETE FROM evaluations WHERE id = ?", (rid,))
            deleted.append(rid)
        conn.commit()
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="No matching reports to delete"
            + (f" (ids: {missing})" if missing else ""),
        )
    return {"ok": True, "deleted": deleted, "missing": missing}


@router.get("/reports/{report_id}")
def get_report(
    report_id: int,
    include_snapshots: bool = True,
    user_id: int | None = Depends(resolve_user_id),
):
    rid = int(report_id)
    with get_conn() as conn:
        if user_id is not None:
            r = conn.execute(
                """
                SELECT id, candidate_name, github_url, linkedin_url, target_role, is_intern,
                       final_score, data_completeness, output_json, created_at,
                       github_data_json, linkedin_data_json, pipeline_json, user_id
                FROM evaluations WHERE id = ? AND user_id = ?
                """,
                (rid, user_id),
            ).fetchone()
        else:
            r = conn.execute(
                """
                SELECT id, candidate_name, github_url, linkedin_url, target_role, is_intern,
                       final_score, data_completeness, output_json, created_at,
                       github_data_json, linkedin_data_json, pipeline_json, user_id
                FROM evaluations WHERE id = ?
                """,
                (rid,),
            ).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    output_json = _parse_json_col(r["output_json"])
    payload: dict = {
        "id": int(r["id"]),
        "candidate_name": str(r["candidate_name"]),
        "github_url": str(r["github_url"]),
        "linkedin_url": str(r["linkedin_url"]),
        "target_role": str(r["target_role"]),
        "is_intern": bool(r["is_intern"]),
        "final_score": float(r["final_score"]),
        "data_completeness": float(r["data_completeness"]),
        "created_at": str(r["created_at"]),
        "report": output_json,
    }
    if include_snapshots:
        payload["github_data"] = _parse_json_col(r["github_data_json"])
        payload["linkedin_data"] = _parse_json_col(r["linkedin_data_json"])
        payload["pipeline"] = _parse_json_col(r["pipeline_json"])
    return payload


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, user_id: int | None = Depends(resolve_user_id)):
    rid = int(report_id)
    with get_conn() as conn:
        if user_id is not None:
            exists = conn.execute(
                "SELECT 1 FROM evaluations WHERE id = ? AND user_id = ?",
                (rid, user_id),
            ).fetchone()
        else:
            exists = conn.execute("SELECT 1 FROM evaluations WHERE id = ?", (rid,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Report not found")
        conn.execute("DELETE FROM evaluations WHERE id = ?", (rid,))
        conn.commit()
    return {"ok": True, "id": rid}
