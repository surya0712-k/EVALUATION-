"""
Legacy stdio MCP entry (LinkedIn only).

Prefer the unified HTTP server: python backend/tools/mcp_server.py  (port 8001)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

_BACKEND = Path(__file__).resolve().parents[1]if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

load_dotenv(_BACKEND / ".env")

from app.analyzers.linkedin import analyze_linkedin_profile as _analyze_linkedin_profile

mcp = FastMCP("Careerlens LinkedIn Tool")


@mcp.tool()
async def analyze_linkedin_profile(
    linkedin_url: str,
    experience_years: float | None = None,
    achievements: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """
    Analyze a LinkedIn profile URL using the same pipeline as Careerlens evaluation.

    Tries Apify (APIFY_API_TOKEN), public scrape, then local JSON fallbacks.
    Optional overrides: experience_years, achievements, skills (when automation is unavailable).
    """
    try:
        return await asyncio.to_thread(
            _analyze_linkedin_profile,
            linkedin_url,
            experience_years=experience_years,
            achievements=achievements,
            skills=skills,
        )
    except Exception as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
