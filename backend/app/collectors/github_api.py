from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests


class GitHubAPICollector:
    def __init__(self, token: str | None = None) -> None:
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "profile-evaluation-agent",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def username_from_url(github_url: str) -> str:
        return github_url.rstrip("/").split("/")[-1]

    def _safe_get(self, url: str) -> Dict[str, Any] | List[Dict[str, Any]]:
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        return response.json()

    def collect(self, github_url: str) -> Dict[str, Any]:
        username = self.username_from_url(github_url)
        profile = self._safe_get(f"{self.base_url}/users/{username}")
        repos = self._safe_get(
            f"{self.base_url}/users/{username}/repos?per_page=100&sort=updated"
        )
        events = self._safe_get(f"{self.base_url}/users/{username}/events/public?per_page=100")

        repo_count = len(repos)
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)
        languages = sorted({r.get("language") for r in repos if r.get("language")})
        readme_presence = sum(1 for r in repos if r.get("description"))

        since = datetime.now(timezone.utc) - timedelta(days=90)
        recent_events = [
            e
            for e in events
            if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) >= since
        ]

        return {
            "username": username,
            "repo_count": repo_count,
            "languages": languages,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "commit_activity_90d": len(recent_events),
            "readme_signal": readme_presence,
            "profile": {
                "name": profile.get("name"),
                "bio": profile.get("bio"),
                "followers": profile.get("followers", 0),
                "public_repos": profile.get("public_repos", 0),
            },
        }
