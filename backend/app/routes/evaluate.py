from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.workflow import build_workflow

router = APIRouter()
workflow = build_workflow()


class EvaluateRequest(BaseModel):
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
def evaluate_profile(payload: EvaluateRequest):
    result = workflow.invoke(payload.model_dump(exclude_none=True))
    return result.get("output", {})
