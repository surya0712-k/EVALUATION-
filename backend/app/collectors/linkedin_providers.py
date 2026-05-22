from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

_LINKEDIN_PUBLIC_TIMEOUT_SECONDS = 20
_PHANTOMBUSTER_BASE = "https://api.phantombuster.com/api/v2"
_APIFY_BASE = "https://api.apify.com/v2"
_APIFY_DEFAULT_URL_ACTOR = "harvestapi/linkedin-profile-scraper"
_APIFY_DEFAULT_SEARCH_ACTOR = "harvestapi/linkedin-profile-search"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _apify_actor_path(actor_id: str) -> str:
    # Apify API expects actor path as "username~actor-name" (not "username/actor-name").
    return actor_id.strip().replace("/", "~")


def _to_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _string_items(values: Any, limit: int = 40) -> List[str]:
    out: List[str] = []
    for item in _to_list(values):
        text = str(item).strip()
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def linkedin_full_name_from_raw(raw: Dict[str, Any], _depth: int = 0) -> str:
    """Best-effort display name from provider JSON (never uses headline)."""
    if not isinstance(raw, dict) or _depth > 3:
        return ""
    for key in ("fullName", "full_name", "name", "displayName"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    fn = str(raw.get("firstName") or raw.get("first_name") or "").strip()
    ln = str(raw.get("lastName") or raw.get("last_name") or "").strip()
    if fn or ln:
        return f"{fn} {ln}".strip()
    for nest_key in ("user", "profile", "basicInfo", "data", "person"):
        nested = raw.get(nest_key)
        if isinstance(nested, dict):
            inner = linkedin_full_name_from_raw(nested, _depth + 1)
            if inner:
                return inner
    return ""


def _experience_years_from_entries(entries: List[Dict[str, Any]]) -> float:
    months = 0
    for entry in entries:
        start = str(entry.get("start") or entry.get("startDate") or "").strip()
        end = str(entry.get("end") or entry.get("endDate") or "").strip()
        if not start:
            continue
        years = re.findall(r"(20\d{2}|19\d{2})", f"{start} {end or 'present'}")
        if not years:
            continue
        if len(years) == 1:
            months += 12
        else:
            try:
                span = max(0, int(years[-1]) - int(years[0]))
                months += max(12, span * 12)
            except ValueError:
                continue
    return round(months / 12.0, 2) if months else 0.0


def _scores_from_linkedin_sections(
    experience_years: float,
    skills_count: int,
    education_count: int,
    certifications_count: int,
    achievements_count: int,
) -> Dict[str, float]:
    career = 38.0
    career += min(25.0, experience_years * 3.5)
    career += min(14.0, achievements_count * 2.0)
    career += min(8.0, education_count * 2.0)
    career += min(8.0, certifications_count * 2.0)

    skill = 32.0
    skill += min(45.0, skills_count * 3.0)
    skill += min(12.0, certifications_count * 3.0)
    skill += min(6.0, achievements_count * 1.0)

    return {
        "career_progression_score": round(max(35.0, min(95.0, career)), 2),
        "skill_relevance_score": round(max(30.0, min(95.0, skill)), 2),
    }


def _unwrap_profile_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """HarvestAPI and other actors often nest the person under profile / linkedinProfile."""
    if linkedin_full_name_from_raw(record):
        return record
    for key in (
        "profile",
        "linkedinProfile",
        "linkedin_profile",
        "person",
        "element",
        "data",
        "item",
        "user",
    ):
        nested = record.get(key)
        if isinstance(nested, dict) and linkedin_full_name_from_raw(nested):
            return nested
    return record


def _extract_first_profile(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("data", "result", "items", "datasetItems", "profiles"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    return _unwrap_profile_record(first)
        return _unwrap_profile_record(payload)
    if isinstance(payload, list) and payload:
        for item in payload:
            if isinstance(item, dict):
                return _unwrap_profile_record(item)
    return None


def fetch_apify_linkedin_profile(linkedin_url: str) -> Tuple[Optional[Dict[str, Any]], str]:
    api_token = os.getenv("APIFY_API_TOKEN", "").strip()
    actor_id = os.getenv("APIFY_LINKEDIN_ACTOR_ID", "").strip()
    if not api_token:
        return None, "APIFY_API_TOKEN missing"

    clean_url = linkedin_url.strip()
    handle = clean_url.rstrip("/").split("/")[-1].strip()
    if not clean_url or clean_url.endswith("/in") or clean_url.endswith("/in/"):
        return None, "linkedin URL incomplete"

    timeout_seconds = os.getenv("APIFY_TIMEOUT_SECONDS", "120")
    actor_attempts: List[tuple[str, Dict[str, Any], str]] = []

    # 1) harvestapi/linkedin-profile-scraper — documented input is profileUrls (URL or public id).
    actor_attempts.append(
        (
            actor_id or _APIFY_DEFAULT_URL_ACTOR,
            {"profileUrls": [clean_url]},
            "profileUrls",
        )
    )
    handle_only = handle if handle and handle.lower() not in {"in", "pub", "company", "school"} else ""
    if handle_only:
        actor_attempts.append(
            (
                actor_id or _APIFY_DEFAULT_URL_ACTOR,
                {"profileUrls": [handle_only]},
                "profileUrls-handle",
            )
        )
    # 2) Search strategy fallback (some actors require searchQuery semantics).
    actor_attempts.append(
        (
            _APIFY_DEFAULT_SEARCH_ACTOR,
            {
                "searchQuery": handle,
                "profileScraperMode": "Full",
                "takePages": 1,
                "maxItems": 1,
            },
            "search-mode",
        )
    )

    # 3) Broad compatibility payload for community variants.
    actor_attempts.append(
        (
            actor_id or _APIFY_DEFAULT_SEARCH_ACTOR,
            {
                "queries": [q for q in [clean_url, handle] if q],
                "searchTerms": [handle] if handle else [],
                "profileUrls": [clean_url],
                "linkedinUrls": [clean_url],
                "maxItems": 1,
            },
            "compat-mode",
        )
    )

    seen: set[tuple[str, str, str]] = set()
    errors: List[str] = []
    for actor, run_input, mode in actor_attempts:
        dedupe_key = (actor, mode, json.dumps(run_input, sort_keys=True))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        actor_path = _apify_actor_path(actor)
        try:
            run = requests.post(
                f"{_APIFY_BASE}/acts/{actor_path}/run-sync-get-dataset-items",
                params={"token": api_token, "timeout": timeout_seconds},
                json=run_input,
                timeout=150,
            )
            run.raise_for_status()
            payload = run.json()
            first = _extract_first_profile(payload)
            if isinstance(first, dict):
                return first, f"success via {actor} ({mode})"
            errors.append(f"{actor} ({mode}): run ok but no items")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "http_error"
            body = ""
            if exc.response is not None:
                body = (exc.response.text or "")[:180].replace("\n", " ")
            errors.append(f"{actor} ({mode}): HTTP {status} {body}".strip())
            continue
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{actor} ({mode}): {exc}")
            continue
    reason = "; ".join(errors[-3:]) if errors else "all actor attempts returned no rows"
    return None, reason


def map_apify_to_collector_shape(raw: Dict[str, Any], linkedin_url: str) -> Dict[str, Any]:
    full_name = linkedin_full_name_from_raw(raw)
    experience_entries_raw = (
        raw.get("experiences")
        or raw.get("experience")
        or raw.get("positions")
        or raw.get("jobs")
        or []
    )
    experience_entries: List[Dict[str, Any]] = [
        x for x in _to_list(experience_entries_raw) if isinstance(x, dict)
    ]
    experience_years = float(raw.get("experience_years") or 0) or _experience_years_from_entries(
        experience_entries
    )

    skills = _string_items(raw.get("skills"), limit=40)
    if not skills and isinstance(raw.get("skills"), list):
        skills = [
            str(s.get("name")).strip()
            for s in raw.get("skills", [])
            if isinstance(s, dict) and str(s.get("name", "")).strip()
        ][:40]

    education = _to_list(raw.get("education") or raw.get("educations"))
    certifications = _to_list(raw.get("certifications") or raw.get("licenses"))

    achievements = _string_items(raw.get("achievements"), limit=20)
    if not achievements:
        headline = str(raw.get("headline") or raw.get("jobTitle") or "").strip()
        company = str(raw.get("companyName") or "").strip()
        location = str(raw.get("location") or "").strip()
        if headline:
            achievements.append(headline)
        if company:
            achievements.append(f"Company: {company}")
        if location:
            achievements.append(f"Location: {location}")
        for exp in experience_entries[:8]:
            role = str(exp.get("title") or exp.get("position") or "").strip()
            org = str(exp.get("companyName") or exp.get("company") or "").strip()
            if role and org:
                achievements.append(f"{role} at {org}")
            elif role:
                achievements.append(role)

    scores = _scores_from_linkedin_sections(
        experience_years=experience_years,
        skills_count=len(skills),
        education_count=len(education),
        certifications_count=len(certifications),
        achievements_count=len(achievements),
    )

    completeness = 0.48
    if experience_years > 0:
        completeness += 0.15
    if skills:
        completeness += 0.18
    if education:
        completeness += 0.08
    if certifications:
        completeness += 0.06
    if achievements:
        completeness += 0.08

    return {
        "linkedin_url": linkedin_url,
        "full_name": full_name,
        "experience_years": round(experience_years, 2),
        "skills": skills,
        "education": education,
        "certifications": certifications,
        "achievements": achievements[:20],
        "career_progression_score": scores["career_progression_score"],
        "skill_relevance_score": scores["skill_relevance_score"],
        "data_source": "apify_linkedin",
        "data_completeness": round(min(0.92, completeness), 2),
        "raw_headline": str(raw.get("headline") or raw.get("jobTitle") or "").strip(),
        "raw_summary": str(raw.get("summary") or raw.get("about") or "")[:500],
    }


def fetch_phantombuster_profile(linkedin_url: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("PHANTOMBUSTER_API_KEY", "").strip()
    agent_id = os.getenv("PHANTOMBUSTER_AGENT_ID", "").strip()
    if not api_key or not agent_id:
        return None

    headers = {"X-Phantombuster-Key-1": api_key, "Content-Type": "application/json"}
    try:
        launch_payload = {
            "id": agent_id,
            "argument": json.dumps({"profileUrls": [linkedin_url], "numberOfProfilesPerLaunch": 1}),
        }
        launch = requests.post(
            f"{_PHANTOMBUSTER_BASE}/agents/launch",
            headers=headers,
            json=launch_payload,
            timeout=25,
        )
        launch.raise_for_status()
        launch_json = launch.json() if launch.content else {}
        container_id = (
            launch_json.get("containerId")
            or (launch_json.get("container") or {}).get("id")
            or launch_json.get("id")
        )
        if not container_id:
            return None

        max_wait = int(os.getenv("PHANTOMBUSTER_MAX_WAIT_SECONDS", "35") or "35")
        deadline = time.time() + max(10, max_wait)
        output_url = ""
        while time.time() < deadline:
            poll = requests.get(
                f"{_PHANTOMBUSTER_BASE}/containers/fetch",
                headers={"X-Phantombuster-Key-1": api_key},
                params={"id": container_id},
                timeout=20,
            )
            poll.raise_for_status()
            poll_json = poll.json() if poll.content else {}
            status = str(poll_json.get("status") or "").lower()
            output_url = (
                poll_json.get("output")
                or poll_json.get("resultObject")
                or poll_json.get("resultUrl")
                or ""
            )
            if status in {"success", "finished", "done"} and output_url:
                break
            if status in {"error", "failed", "aborted"}:
                return None
            time.sleep(3)

        if not output_url:
            return None

        output_res = requests.get(output_url, timeout=20)
        output_res.raise_for_status()
        data = output_res.json()
        profile = _extract_first_profile(data)
        return profile if isinstance(profile, dict) else None
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        return None


def map_phantombuster_to_collector_shape(raw: Dict[str, Any], linkedin_url: str) -> Dict[str, Any]:
    experience_entries_raw = (
        raw.get("experiences")
        or raw.get("experience")
        or raw.get("positions")
        or raw.get("workExperiences")
        or []
    )
    experience_entries: List[Dict[str, Any]] = [
        x for x in _to_list(experience_entries_raw) if isinstance(x, dict)
    ]
    experience_years = float(raw.get("experience_years") or 0) or _experience_years_from_entries(
        experience_entries
    )

    skills = _string_items(raw.get("skills"), limit=40)
    if not skills and isinstance(raw.get("skills"), list):
        skills = [
            str(s.get("name")).strip()
            for s in raw.get("skills", [])
            if isinstance(s, dict) and str(s.get("name", "")).strip()
        ][:40]

    education = _to_list(raw.get("education") or raw.get("educations"))
    certifications = _to_list(raw.get("certifications") or raw.get("licenses"))

    achievements = _string_items(raw.get("achievements"), limit=20)
    if not achievements:
        headline = str(raw.get("headline") or raw.get("title") or "").strip()
        summary = str(raw.get("summary") or raw.get("about") or "").strip()
        if headline:
            achievements.append(headline)
        if summary:
            achievements.append(summary[:180])
        for exp in experience_entries[:8]:
            role = str(exp.get("title") or exp.get("position") or "").strip()
            company = str(exp.get("company") or exp.get("companyName") or "").strip()
            if role and company:
                achievements.append(f"{role} at {company}")
            elif role:
                achievements.append(role)

    scores = _scores_from_linkedin_sections(
        experience_years=experience_years,
        skills_count=len(skills),
        education_count=len(education),
        certifications_count=len(certifications),
        achievements_count=len(achievements),
    )

    completeness = 0.45
    if experience_years > 0:
        completeness += 0.15
    if skills:
        completeness += 0.2
    if education:
        completeness += 0.07
    if certifications:
        completeness += 0.06
    if achievements:
        completeness += 0.07

    return {
        "linkedin_url": linkedin_url,
        "full_name": linkedin_full_name_from_raw(raw),
        "experience_years": round(experience_years, 2),
        "skills": skills,
        "education": education,
        "certifications": certifications,
        "achievements": achievements[:20],
        "career_progression_score": scores["career_progression_score"],
        "skill_relevance_score": scores["skill_relevance_score"],
        "data_source": "phantombuster",
        "data_completeness": round(min(0.92, completeness), 2),
        "raw_headline": str(raw.get("headline") or "").strip(),
        "raw_summary": str(raw.get("summary") or "")[:500],
    }


def _extract_profile_json_ld(html: str) -> Optional[Dict[str, Any]]:
    scripts = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    )
    for raw_script in scripts:
        try:
            payload = json.loads(raw_script.strip())
        except json.JSONDecodeError:
            continue

        candidates: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            if isinstance(payload.get("@graph"), list):
                candidates.extend([x for x in payload["@graph"] if isinstance(x, dict)])
            candidates.append(payload)
        elif isinstance(payload, list):
            candidates.extend([x for x in payload if isinstance(x, dict)])

        for item in candidates:
            if str(item.get("@type", "")).lower() in {"person", "profilepage"}:
                return item
    return None


def fetch_public_linkedin_profile(linkedin_url: str) -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(
            linkedin_url.strip(),
            headers={"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"},
            timeout=_LINKEDIN_PUBLIC_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if res.status_code >= 400:
            return None
        html = res.text or ""
        lower = html.lower()
        if "authwall" in lower or "sign in" in lower and "linkedin" in lower:
            return None

        ld = _extract_profile_json_ld(html) or {}
        headline = ""
        if isinstance(ld.get("description"), str):
            headline = ld["description"].strip()
        if not headline:
            m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
            if m:
                headline = re.sub(r"\s+", " ", m.group(1)).strip()

        name = ""
        if isinstance(ld.get("name"), str):
            name = ld["name"].strip()
        if not name and headline:
            name = headline.split("|")[0].split(" - ")[0].strip()

        # Skills are usually not available publicly; keep parser conservative.
        skills: List[str] = []
        achievements: List[str] = []
        if name:
            achievements.append(f"LinkedIn profile detected: {name}")
        if headline:
            achievements.append(headline[:180])

        if not achievements:
            return None

        return {
            "name": name,
            "headline": headline,
            "skills": skills,
            "achievements": achievements,
            "raw_html_length": len(html),
        }
    except requests.RequestException:
        return None


def map_public_profile_to_collector_shape(raw: Dict[str, Any], linkedin_url: str) -> Dict[str, Any]:
    skills_raw = raw.get("skills") or []
    skills: List[str] = []
    if isinstance(skills_raw, list):
        skills = [str(s).strip() for s in skills_raw if str(s).strip()][:40]

    achievements_raw = raw.get("achievements") or []
    achievements: List[str] = []
    if isinstance(achievements_raw, list):
        achievements = [str(a).strip() for a in achievements_raw if str(a).strip()][:20]

    headline = (raw.get("headline") or "").strip()
    full_name = str(raw.get("name") or "").strip()
    if headline and headline not in achievements:
        achievements.insert(0, headline)

    completeness = 0.48
    if skills:
        completeness = min(0.72, completeness + 0.12)
    if len(achievements) >= 2:
        completeness = min(0.72, completeness + 0.1)

    scores = _scores_from_linkedin_sections(
        experience_years=0.0,
        skills_count=len(skills),
        education_count=0,
        certifications_count=0,
        achievements_count=len(achievements),
    )

    return {
        "linkedin_url": linkedin_url,
        "full_name": full_name,
        "experience_years": 0.0,
        "skills": skills,
        "education": [],
        "certifications": [],
        "achievements": achievements,
        "career_progression_score": scores["career_progression_score"],
        "skill_relevance_score": scores["skill_relevance_score"],
        "data_source": "public_scrape",
        "data_completeness": completeness,
        "raw_headline": headline,
        "raw_summary": "",
    }
