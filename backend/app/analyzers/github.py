from __future__ import annotations

import os
from typing import Any

from app.collectors.github_api import GitHubAPICollector


def _activity_tier(commit_activity_90d: int, repo_count: int) -> str:
    if commit_activity_90d >= 50:
        return "high"
    if commit_activity_90d >= 10 or repo_count >= 5:
        return "moderate"
    if commit_activity_90d > 0:
        return "low"
    return "inactive"


def _github_warnings(raw: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if raw and int(raw.get("repo_count") or 0) > 0 and int(raw.get("commit_activity_90d") or 0) == 0:
        warnings.append(
            "No public GitHub pushes detected in the last 90 days for this username. "
            "Work on private repos, unpushed commits, or commits under another account "
            "will not appear in this score."
        )
    if not os.getenv("GITHUB_TOKEN"):
        warnings.append(
            "GITHUB_TOKEN is not set — commit scans may hit rate limits."
        )
    return warnings


def _highlights(data: dict[str, Any]) -> list[str]:
    profile = data.get("profile") or {}
    lines: list[str] = []
    name = (profile.get("name") or data.get("username") or "").strip()
    if name:
        lines.append(f"Profile: {name}")

    langs = data.get("languages") or []
    if langs:
        lines.append(f"Languages across repos: {', '.join(langs[:8])}")

    repo_count = int(data.get("repo_count") or 0)
    stars = int(data.get("total_stars") or 0)
    if repo_count:
        lines.append(f"{repo_count} public repos · {stars} total stars")

    commit_90d = int(data.get("commit_activity_90d") or 0)
    tier = _activity_tier(commit_90d, repo_count)
    if tier == "inactive":
        lines.append("No strong public commit activity detected in the last 90 days.")
    else:
        lines.append(
            f"90-day activity index: {commit_90d} ({tier}) — "
            f"repo scan: {data.get('commits_repo_scan_90d', 0)}, "
            f"push events: {data.get('push_commits_90d', 0)}, "
            f"repos pushed: {data.get('repos_pushed_90d', 0)}"
        )
    return lines


def build_github_analysis(data: dict[str, Any]) -> dict[str, Any]:
    profile = data.get("profile") or {}
    commit_90d = int(data.get("commit_activity_90d") or 0)
    repo_count = int(data.get("repo_count") or 0)
    return {
        "username": data.get("username"),
        "display_name": profile.get("name"),
        "bio": profile.get("bio"),
        "activity_tier_90d": _activity_tier(commit_90d, repo_count),
        "github_signals": {
            "commit_activity_index_90d": commit_90d,
            "repos_pushed_90d": data.get("repos_pushed_90d"),
            "public_push_commits_estimated_90d": data.get("push_commits_90d"),
            "commits_repo_scan_90d": data.get("commits_repo_scan_90d"),
            "public_repo_count": repo_count,
        },
        "languages": data.get("languages", []),
        "total_stars": data.get("total_stars"),
        "total_forks": data.get("total_forks"),
        "followers": profile.get("followers"),
        "public_repos": profile.get("public_repos"),
        "highlights": _highlights(data),
        "warnings": _github_warnings(data),
    }


def analyze_github_profile(github_url: str) -> dict[str, Any]:
    url = (github_url or "").strip()
    if not url:
        raise ValueError("github_url is required")
    if "github.com" not in url.lower():
        raise ValueError("Expected a GitHub profile URL (e.g. https://github.com/octocat)")

    token = os.getenv("GITHUB_TOKEN") or None
    collector = GitHubAPICollector(token=token)
    raw = collector.collect(url)
    analysis = build_github_analysis(raw)
    return {
        "github_url": url.rstrip("/"),
        "raw": raw,
        "analysis": analysis,
    }
