"""
Legacy stdio MCP entry (GitHub only).

Prefer the unified HTTP server: python backend/tools/mcp_server.py  (port 8001)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

load_dotenv(_BACKEND / ".env")

from app.analyzers.github import analyze_github_profile as _analyze_github_profile

mcp = FastMCP("Careerlens GitHub Tool (stdio)") 

@mcp.tool()
async def analyze_github_profile(github_url: str) -> dict[str, Any]:
    """
    Analyze a public GitHub profile URL.

    Returns repo/language stats, 90-day commit activity signals (same metrics as
    Careerlens evaluation), and a short highlights summary.
    """
    try:
        return await asyncio.to_thread(_analyze_github_profile, github_url)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
