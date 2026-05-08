from __future__ import annotations

import os
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

    def _push_activity_in_window(self, username: str, since: datetime) -> tuple[int, int]:
        """
        Paginate public events; count commits on PushEvents in the time window.
        Returns (approx_commit_count, repos_touched_by_push_in_window) — the latter from distinct repo names in PushEvents.
        """
        commitish = 0
        push_repos: set[str] = set()
        page = 1
        max_pages = 20
        reached_old = False

        while page <= max_pages and not reached_old:
            url = f"{self.base_url}/users/{username}/events/public?per_page=100&page={page}"
            try:
                events = self._safe_get(url)
            except requests.HTTPError:
                break
            if not isinstance(events, list) or not events:
                break

            for e in events:
                created_raw = e.get("created_at")
                if not created_raw:
                    continue
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if created < since:
                    reached_old = True
                    continue
                if e.get("type") != "PushEvent":
                    continue
                repo = (e.get("repo") or {}).get("name") or ""
                if repo:
                    push_repos.add(repo)
                commits = (e.get("payload") or {}).get("commits") or []
                commitish += len(commits) if commits else 1

            if len(events) < 100:
                break
            page += 1

        return commitish, len(push_repos)

    def _count_commits_across_repos(
        self, username: str, repos: List[Dict[str, Any]], since: datetime
    ) -> int:
        """
        Walk each listed repo's commits with `author=<login>` and `since=` (REST API).
        Captures work that never appears on /users/{login}/events/public (orgs, forks,
        rebases, or events falling off the activity feed).
        """
        since_s = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        max_repos = max(1, min(50, int(os.getenv("GITHUB_COMMIT_SCAN_MAX_REPOS", "35"))))
        total = 0

        for r in repos[:max_repos]:
            full = (r.get("full_name") or "").strip()
            if not full or "/" not in full:
                name = r.get("name")
                if not name:
                    continue
                full = f"{username}/{name}"
            owner, repo = full.split("/", 1)
            page = 1
            per_page = 100
            while page <= 25:
                url = f"{self.base_url}/repos/{owner}/{repo}/commits"
                params = {
                    "author": username,
                    "since": since_s,
                    "per_page": per_page,
                    "page": page,
                }
                try:
                    resp = self.session.get(url, params=params, timeout=20)
                    resp.raise_for_status()
                    batch = resp.json()
                except requests.HTTPError:
                    break
                if not isinstance(batch, list) or not batch:
                    break
                total += len(batch)
                if len(batch) < per_page:
                    break
                page += 1

        return total

    @staticmethod
    def _repos_pushed_since(repos: List[Dict[str, Any]], since: datetime) -> int:
        n = 0
        for r in repos:
            pu = r.get("pushed_at")
            if not pu:
                continue
            try:
                ts = datetime.fromisoformat(pu.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts >= since:
                n += 1
        return n

    def collect(self, github_url: str) -> Dict[str, Any]:
        username = self.username_from_url(github_url)
        profile = self._safe_get(f"{self.base_url}/users/{username}")
        repos = self._safe_get(
            f"{self.base_url}/users/{username}/repos?per_page=100&sort=updated"
        )

        repo_count = len(repos)
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)
        languages = sorted({r.get("language") for r in repos if r.get("language")})
        readme_presence = sum(1 for r in repos if r.get("description"))

        since = datetime.now(timezone.utc) - timedelta(days=90)
        repos_pushed_90d = self._repos_pushed_since(repos, since)
        push_commits_90d, push_repo_events = self._push_activity_in_window(username, since)
        commits_repo_scan_90d = self._count_commits_across_repos(username, repos, since)

        # Combine: per-repo commit scan (most faithful for public repos) + public PushEvents +
        # repos with fresh pushed_at (covers some cases where commit list pagination differs).
        commit_activity_90d = max(
            commits_repo_scan_90d,
            push_commits_90d,
            repos_pushed_90d * 2,
            push_repo_events,
        )

        return {
            "username": username,
            "repo_count": repo_count,
            "languages": languages,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "commit_activity_90d": int(commit_activity_90d),
            "repos_pushed_90d": repos_pushed_90d,
            "push_commits_90d": int(push_commits_90d),
            "commits_repo_scan_90d": int(commits_repo_scan_90d),
            "readme_signal": readme_presence,
            "profile": {
                "name": profile.get("name"),
                "bio": profile.get("bio"),
                "followers": profile.get("followers", 0),
                "public_repos": profile.get("public_repos", 0),
            },
        }
