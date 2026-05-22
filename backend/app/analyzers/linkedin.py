from __future__ import annotations

import os
from typing import Any

from app.collectors.linkedin_phantombuster import LinkedInCollector


def _enrichment_tier(data_source: str) -> str:
    if data_source == "placeholder":
        return "placeholder"
    if data_source in {"apify_linkedin", "apify_linkedin_search", "phantombuster", "public_scrape"}:
        return "enriched"
    if data_source in {"local_json_file", "local_json_auto", "user_supplied"}:
        return "manual"
    return "partial"


def apply_linkedin_overrides(
    linkedin_data: dict[str, Any],
    *,
    experience_years: float | None = None,
    achievements: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    data = dict(linkedin_data)
    if experience_years is not None:
        try:
            data["experience_years"] = float(experience_years)
        except (TypeError, ValueError):
            pass
    if isinstance(achievements, list) and achievements:
        data["achievements"] = [str(x).strip() for x in achievements if str(x).strip()]
    if isinstance(skills, list) and skills:
        data["skills"] = [str(x).strip() for x in skills if str(x).strip()]

    user_touched = (
        experience_years is not None
        or (isinstance(achievements, list) and achievements)
        or (isinstance(skills, list) and skills)
    )
    if user_touched:
        data["data_source"] = "user_supplied"
        data["data_completeness"] = max(float(data.get("data_completeness", 0.2)), 0.72)
        data["career_progression_score"] = max(
            float(data.get("career_progression_score", 40)),
            52.0,
        )
        data["skill_relevance_score"] = max(
            float(data.get("skill_relevance_score", 40)),
            52.0,
        )
    return data


def _linkedin_warnings(
    linkedin_url: str,
    data: dict[str, Any],
    debug: dict[str, Any] | None = None,
) -> list[str]:
    warnings: list[str] = []
    url = (linkedin_url or "").strip()
    if url.endswith("/in") or url.endswith("/in/"):
        warnings.append(
            "LinkedIn URL looks incomplete (it ends at /in/). Use a full profile URL like "
            "https://www.linkedin.com/in/<username>/."
        )
    if data.get("data_source") == "placeholder":
        if not os.getenv("APIFY_API_TOKEN", "").strip():
            warnings.append(
                "LinkedIn was not enriched: APIFY_API_TOKEN is not available to the API server. "
                "Add it to backend/.env (then restart Docker: docker compose up --build). "
                "Apify Console runs use your account token; the backend must have the same token."
            )
        else:
            warnings.append(
                "LinkedIn was not enriched from Apify (token is set but the actor returned no usable rows). "
                "Check APIFY_LINKEDIN_ACTOR_ID matches your actor (harvestapi/linkedin-profile-scraper) "
                "or use backend/linkedin_profile.json. Until then, scores use GitHub-heavy weighting."
            )
        for attempt in (debug or {}).get("attempts", []):
            if attempt.get("provider") == "apify" and attempt.get("status") == "failed":
                reason = str(attempt.get("reason") or "").strip()
                if reason and reason not in warnings:
                    warnings.append(f"Apify detail: {reason}")
                break
    return warnings


def _highlights(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    name = str(data.get("full_name") or "").strip()
    if name:
        lines.append(f"Profile: {name}")
    else:
        lines.append("Profile: name not available from data source")

    exp = float(data.get("experience_years") or 0)
    if exp > 0:
        lines.append(f"Experience: {exp:.1f} years (reported)")

    skills = data.get("skills") or []
    if skills:
        preview = ", ".join(str(s) for s in skills[:10])
        suffix = "…" if len(skills) > 10 else ""
        lines.append(f"Skills ({len(skills)}): {preview}{suffix}")

    achievements = data.get("achievements") or []
    if achievements:
        lines.append(f"Achievements / highlights: {len(achievements)} item(s)")

    source = str(data.get("data_source") or "unknown")
    tier = _enrichment_tier(source)
    completeness = round(float(data.get("data_completeness", 0)) * 100)
    lines.append(
        f"Data source: {source} ({tier}) · completeness ~{completeness}% · "
        f"career score {float(data.get('career_progression_score', 0)):.0f} · "
        f"skill score {float(data.get('skill_relevance_score', 0)):.0f}"
    )
    return lines


def build_linkedin_analysis(
    linkedin_url: str,
    data: dict[str, Any],
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = str(data.get("data_source") or "placeholder")
    skills = data.get("skills") or []
    achievements = data.get("achievements") or []
    return {
        "full_name": data.get("full_name"),
        "enrichment_tier": _enrichment_tier(source),
        "data_source": source,
        "linkedin_signals": {
            "experience_years": data.get("experience_years"),
            "skills_count": len(skills) if isinstance(skills, list) else 0,
            "achievements_count": len(achievements) if isinstance(achievements, list) else 0,
            "career_progression_score": data.get("career_progression_score"),
            "skill_relevance_score": data.get("skill_relevance_score"),
            "data_completeness": data.get("data_completeness"),
        },
        "skills": skills[:20] if isinstance(skills, list) else [],
        "achievements": achievements[:8] if isinstance(achievements, list) else [],
        "highlights": _highlights(data),
        "warnings": _linkedin_warnings(linkedin_url, data, debug),
    }


def analyze_linkedin_profile(
    linkedin_url: str,
    *,
    experience_years: float | None = None,
    achievements: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    url = (linkedin_url or "").strip()
    if not url:
        raise ValueError("linkedin_url is required")
    lower = url.lower()
    if "linkedin.com" not in lower or "/in/" not in lower:
        raise ValueError(
            "Expected a LinkedIn profile URL with /in/ "
            "(e.g. https://www.linkedin.com/in/username/)"
        )

    collector = LinkedInCollector()
    raw, debug = collector.collect_with_debug(url)
    raw = apply_linkedin_overrides(
        raw,
        experience_years=experience_years,
        achievements=achievements,
        skills=skills,
    )
    analysis = build_linkedin_analysis(url, raw, debug)
    return {
        "linkedin_url": url.rstrip("/"),
        "raw": raw,
        "analysis": analysis,
        "debug": debug,
    }
