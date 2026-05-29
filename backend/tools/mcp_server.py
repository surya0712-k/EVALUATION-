"""
CareerLens unified FastMCP server (HTTP).

Runs on a real port (default 8090) using streamable HTTP transport.
Not bundled inside the FastAPI app on port 8000.

Start:
  python backend/tools/mcp_server.py
  MCP_HOST=0.0.0.0 MCP_PORT=8001 python backend/tools/mcp_server.py

Endpoints (default):
  MCP URL:  http://127.0.0.1:8090/mcp
  Health:   http://127.0.0.1:8090/health
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

load_dotenv(_BACKEND / ".env")

from app.analyzers.github import analyze_github_profile as _analyze_github
from app.analyzers.linkedin import analyze_linkedin_profile as _analyze_linkedin

_host = os.getenv("MCP_HOST", "0.0.0.0").strip() or "0.0.0.0"
_port = int(os.getenv("MCP_PORT", "8090"))
_transport = os.getenv("MCP_TRANSPORT", "streamable-http").strip() or "streamable-http"

mcp = FastMCP(
    "Careerlens",
    instructions=(
        "CareerLens profile evaluation tools for HR and recruiters. "
        "Analyze public GitHub and LinkedIn profiles."
    ),
    host=_host,
    port=_port,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "careerlens-mcp",
            "transport": _transport,
            "mcp_url": f"http://{_host}:{_port}/mcp",
            "tools": ["analyze_github_profile", "analyze_linkedin_profile"],
            "apify_configured": bool(os.getenv("APIFY_API_TOKEN", "").strip()),
            "github_token_configured": bool(os.getenv("GITHUB_TOKEN", "").strip()),
        }
    )


@mcp.tool()
async def analyze_github_profile(github_url: str) -> dict[str, Any]:
    """
    Analyze a public GitHub profile URL.

    Returns repo/language stats, 90-day activity signals, and HR highlights.
    """
    try:
        return await asyncio.to_thread(_analyze_github, github_url)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool()
async def analyze_linkedin_profile(
    linkedin_url: str,
    experience_years: float | None = None,
    achievements: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """
    Analyze a LinkedIn profile URL (Apify, scrape, or JSON fallbacks).

    Optional overrides when automation is unavailable: experience_years, achievements, skills.
    """
    try:
        return await asyncio.to_thread(
            _analyze_linkedin,
            linkedin_url,
            experience_years=experience_years,
            achievements=achievements,
            skills=skills,
        )
    except Exception as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    print(f"CareerLens MCP server: {_transport} at http://{_host}:{_port}/mcp", flush=True)
    print(f"Health check: http://127.0.0.1:{_port}/health", flush=True)
    mcp.run(transport=_transport)  # type: ignore[arg-type]
