from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analyzers.github import analyze_github_profile
from app.analyzers.linkedin import analyze_linkedin_profile

router = APIRouter()


class GitHubAnalyzeRequest(BaseModel):
    github_url: str = Field(..., examples=["https://github.com/octocat"])


class LinkedInAnalyzeRequest(BaseModel):
    linkedin_url: str = Field(..., examples=["https://www.linkedin.com/in/sample-user/"])
    linkedin_experience_years: Optional[float] = Field(default=None)
    linkedin_achievements: Optional[List[str]] = Field(default=None)
    linkedin_skills: Optional[List[str]] = Field(default=None)


@router.post("/analyze/github")
def analyze_github(payload: GitHubAnalyzeRequest):
    return analyze_github_profile(payload.github_url.strip())


@router.post("/analyze/linkedin")
def analyze_linkedin(payload: LinkedInAnalyzeRequest):
    return analyze_linkedin_profile(
        payload.linkedin_url.strip(),
        experience_years=payload.linkedin_experience_years,
        achievements=payload.linkedin_achievements,
        skills=payload.linkedin_skills,
    )
