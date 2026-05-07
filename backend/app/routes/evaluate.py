from __future__ import annotations

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


@router.post("/evaluate")
def evaluate_profile(payload: EvaluateRequest):
    result = workflow.invoke(payload.model_dump())
    return result.get("output", {})
