from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from app.collectors.linkedin_providers import (
    fetch_apify_linkedin_profile,
    fetch_public_linkedin_profile,
    map_apify_to_collector_shape,
    map_public_profile_to_collector_shape,
)

# Auto-loaded if present (copy linkedin_profile.example.json → linkedin_profile.json).
_DEFAULT_PROFILE_REL = Path("linkedin_profile.json")


class LinkedInCollector:
    """
    LinkedIn data sources (first match wins):

    1. **Apify LinkedIn Profile Search Scraper** — set ``APIFY_API_TOKEN``.
    2. **Public scraper** — best-effort pull from the public LinkedIn URL.
    3. **Local JSON** — ``LINKEDIN_PROFILE_JSON`` path to a file (dev / manual).
    4. **Default file** — ``backend/linkedin_profile.json`` if present (gitignored; copy from
       ``linkedin_profile.example.json``).
    5. **Placeholder** — sparse defaults so the pipeline still runs (scores are not verified).

    The filename ``linkedin_phantombuster`` is legacy: PhantomBuster was never wired here
    because each Phantom uses its own launch arguments and async buckets. If you add a
    provider adapter later, map it into the same shape this collector returns.
    """

    @staticmethod
    def _placeholder(linkedin_url: str) -> Dict[str, Any]:
        return {
            "linkedin_url": linkedin_url,
            "full_name": "",
            "experience_years": 0,
            "skills": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "career_progression_score": 40,
            "skill_relevance_score": 40,
            "data_source": "placeholder",
            "data_completeness": 0.2,
        }

    @staticmethod
    def _from_json_file(linkedin_url: str, path: Path) -> Dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        skills = data.get("skills") or []
        achievements = data.get("achievements") or []
        if not isinstance(skills, list):
            skills = []
        if not isinstance(achievements, list):
            achievements = []
        fn = str(data.get("full_name") or data.get("name") or "").strip()
        return {
            "linkedin_url": linkedin_url,
            "full_name": fn,
            "experience_years": float(data.get("experience_years", 0) or 0),
            "skills": [str(s).strip() for s in skills if str(s).strip()],
            "education": data.get("education") or [],
            "certifications": data.get("certifications") or [],
            "achievements": [str(a).strip() for a in achievements if str(a).strip()],
            "career_progression_score": float(data.get("career_progression_score", 55)),
            "skill_relevance_score": float(data.get("skill_relevance_score", 55)),
            "data_source": "local_json_file",
            "data_completeness": float(data.get("data_completeness", 0.75)),
        }

    def collect(self, linkedin_url: str) -> Dict[str, Any]:
        data, _debug = self.collect_with_debug(linkedin_url)
        return data

    def collect_with_debug(self, linkedin_url: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        debug: Dict[str, Any] = {
            "url": linkedin_url,
            "attempts": [],
        }

        apify, apify_reason = fetch_apify_linkedin_profile(linkedin_url)
        if apify:
            debug["attempts"].append({"provider": "apify", "status": "success"})
            return map_apify_to_collector_shape(apify, linkedin_url), debug
        debug["attempts"].append(
            {
                "provider": "apify",
                "status": "failed",
                "reason": apify_reason or "no items, token/actor issue, timeout, or parse mismatch",
            }
        )

        scraped = fetch_public_linkedin_profile(linkedin_url)
        if scraped:
            debug["attempts"].append({"provider": "public_scrape", "status": "success"})
            return map_public_profile_to_collector_shape(scraped, linkedin_url), debug
        debug["attempts"].append(
            {
                "provider": "public_scrape",
                "status": "failed",
                "reason": "auth wall, blocked page, or no parseable profile data",
            }
        )

        raw_path = os.getenv("LINKEDIN_PROFILE_JSON", "").strip()
        if raw_path:
            path = Path(raw_path).expanduser()
            if path.is_file():
                loaded = self._from_json_file(linkedin_url, path)
                if loaded:
                    debug["attempts"].append(
                        {"provider": "json_env_path", "status": "success", "path": str(path)}
                    )
                    return loaded, debug
                debug["attempts"].append(
                    {
                        "provider": "json_env_path",
                        "status": "failed",
                        "path": str(path),
                        "reason": "file unreadable or invalid JSON",
                    }
                )
            else:
                debug["attempts"].append(
                    {"provider": "json_env_path", "status": "failed", "reason": "file not found"}
                )

        backend_root = Path(__file__).resolve().parents[2]
        default_file = backend_root / _DEFAULT_PROFILE_REL
        if default_file.is_file():
            loaded = self._from_json_file(linkedin_url, default_file)
            if loaded:
                out = loaded
                out["data_source"] = "local_json_auto"
                debug["attempts"].append(
                    {"provider": "json_default_file", "status": "success", "path": str(default_file)}
                )
                return out, debug
            debug["attempts"].append(
                {
                    "provider": "json_default_file",
                    "status": "failed",
                    "path": str(default_file),
                    "reason": "file unreadable or invalid JSON",
                }
            )
        else:
            debug["attempts"].append(
                {"provider": "json_default_file", "status": "failed", "reason": "file not found"}
            )

        debug["final"] = "placeholder"
        return self._placeholder(linkedin_url), debug
