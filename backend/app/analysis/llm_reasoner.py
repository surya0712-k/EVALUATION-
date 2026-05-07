from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_JSON_INSTRUCTIONS = """Respond with a single JSON object only (no markdown), using this shape:
{
  "strengths": ["short bullet strings"],
  "weaknesses": ["short bullet strings"],
  "hiring_recommendations": ["actionable strings for recruiters"],
  "suggested_role_fit": ["role titles that fit the candidate"],
  "intern_criteria": {
    "code_quality_and_structure": 0-100,
    "agent_design_clarity": 0-100,
    "reasoning_quality_llm_outputs": 0-100,
    "scoring_logic_fairness": 0-100,
    "handling_incomplete_data": 0-100
  }
}
If is_intern is false, set "intern_criteria" to {}.
Base every statement on the provided data; if data is sparse, say so explicitly in weaknesses."""


def _heuristic_analysis(features: Dict[str, Any], target_role: str, is_intern: bool) -> Dict[str, Any]:
    category_scores = features["category_scores"]
    strengths: List[str] = []
    weaknesses: List[str] = []

    for category, score in category_scores.items():
        if score >= 70:
            strengths.append(f"Strong {category.replace('_', ' ')} signal ({score:.1f})")
        elif score < 45:
            weaknesses.append(f"Needs improvement in {category.replace('_', ' ')} ({score:.1f})")

    if not strengths:
        strengths.append("Shows baseline cross-platform profile evidence.")
    if not weaknesses:
        weaknesses.append("No major weak category detected from available data.")

    hiring_recommendations = [
        f"Shortlist for {target_role} if practical assessment matches profile signals.",
        "Use a role-specific coding/task round to validate profile-derived strengths.",
    ]

    suggested_role_fit = [target_role]
    if category_scores["project_quality"] > 75:
        suggested_role_fit.append("Open Source Engineer")
    if category_scores["skills"] > 70:
        suggested_role_fit.append("Full Stack Developer")

    intern_criteria: Dict[str, float] = {}
    if is_intern:
        intern_criteria = {
            "code_quality_and_structure": min(100.0, category_scores["project_quality"]),
            "agent_design_clarity": min(100.0, (category_scores["skills"] + category_scores["experience"]) / 2),
            "reasoning_quality_llm_outputs": min(100.0, (category_scores["skills"] + 10)),
            "scoring_logic_fairness": 80.0,
            "handling_incomplete_data": min(100.0, features.get("data_completeness", 0.5) * 100),
        }

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "hiring_recommendations": hiring_recommendations,
        "suggested_role_fit": list(dict.fromkeys(suggested_role_fit)),
        "intern_criteria": intern_criteria,
    }


def _compact_github(github_data: Dict[str, Any]) -> Dict[str, Any]:
    if not github_data:
        return {}
    return {
        "username": github_data.get("username"),
        "repo_count": github_data.get("repo_count"),
        "languages": github_data.get("languages", [])[:12],
        "total_stars": github_data.get("total_stars"),
        "total_forks": github_data.get("total_forks"),
        "commit_activity_90d": github_data.get("commit_activity_90d"),
        "profile": github_data.get("profile", {}),
    }


def _compact_linkedin(linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
    if not linkedin_data:
        return {}
    return {
        "experience_years": linkedin_data.get("experience_years"),
        "skills": (linkedin_data.get("skills") or [])[:15],
        "achievements": (linkedin_data.get("achievements") or [])[:8],
        "data_completeness": linkedin_data.get("data_completeness"),
        "data_source": linkedin_data.get("data_source"),
    }


def _coerce_float_scores(d: Any) -> Dict[str, float]:
    if not isinstance(d, dict):
        return {}
    out: Dict[str, float] = {}
    for k, v in d.items():
        try:
            out[str(k)] = max(0.0, min(100.0, float(v)))
        except (TypeError, ValueError):
            continue
    return out


def _normalize_llm_payload(
    data: Dict[str, Any],
    *,
    target_role: str,
    is_intern: bool,
    heuristic: Dict[str, Any],
) -> Dict[str, Any]:
    def as_str_list(key: str, fallback: List[str]) -> List[str]:
        raw = data.get(key)
        if not isinstance(raw, list):
            return list(fallback)
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out or list(fallback)

    strengths = as_str_list("strengths", heuristic["strengths"])
    weaknesses = as_str_list("weaknesses", heuristic["weaknesses"])
    hiring = as_str_list("hiring_recommendations", heuristic["hiring_recommendations"])
    roles = as_str_list("suggested_role_fit", heuristic["suggested_role_fit"])
    if target_role and target_role not in roles:
        roles = [target_role, *roles]

    intern_raw = data.get("intern_criteria")
    if is_intern:
        intern_criteria = _coerce_float_scores(intern_raw) if isinstance(intern_raw, dict) else {}
        if len(intern_criteria) < 3:
            intern_criteria = {**heuristic.get("intern_criteria", {}), **intern_criteria}
    else:
        intern_criteria = {}

    return {
        "strengths": strengths[:12],
        "weaknesses": weaknesses[:12],
        "hiring_recommendations": hiring[:10],
        "suggested_role_fit": list(dict.fromkeys(roles))[:8],
        "intern_criteria": intern_criteria,
    }


def _llm_analyze(
    *,
    features: Dict[str, Any],
    target_role: str,
    is_intern: bool,
    github_data: Dict[str, Any],
    linkedin_data: Dict[str, Any],
) -> Dict[str, Any]:
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    genai.configure(api_key=api_key)

    heuristic = _heuristic_analysis(features, target_role, is_intern)

    user_payload = {
        "target_role": target_role,
        "is_intern": is_intern,
        "derived_scores": {
            "category_scores": features.get("category_scores"),
            "tech_depth_score": features.get("tech_depth_score"),
            "consistency_score": features.get("consistency_score"),
            "open_source_contribution_signal": features.get("open_source_contribution_signal"),
            "data_completeness": features.get("data_completeness"),
        },
        "github_summary": _compact_github(github_data),
        "linkedin_summary": _compact_linkedin(linkedin_data),
    }

    system = (
        "You are an experienced technical recruiter and engineer. "
        "You write fair, concise hiring notes from structured profile signals. "
        + _JSON_INSTRUCTIONS
    )

    model = genai.GenerativeModel(model_name, system_instruction=system)
    response = model.generate_content(
        json.dumps(user_payload, indent=2),
        generation_config=genai.GenerationConfig(
            temperature=0.35,
            response_mime_type="application/json",
        ),
    )

    if not response.candidates:
        raise RuntimeError("Gemini returned no response (check safety filters or API key)")

    text = (response.text or "").strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned non-object JSON")

    return _normalize_llm_payload(parsed, target_role=target_role, is_intern=is_intern, heuristic=heuristic)


def analyze_candidate(
    features: Dict[str, Any],
    target_role: str,
    is_intern: bool,
    github_data: Optional[Dict[str, Any]] = None,
    linkedin_data: Optional[Dict[str, Any]] = None,
    warn_sink: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    If GEMINI_API_KEY is set, runs a Gemini narrative pass over the features + summaries.
    Otherwise (or on failure), falls back to deterministic heuristics.
    """
    github_data = github_data or {}
    linkedin_data = linkedin_data or {}

    use_llm = bool(os.getenv("GEMINI_API_KEY", "").strip())
    if not use_llm:
        return _heuristic_analysis(features, target_role, is_intern)

    try:
        return _llm_analyze(
            features=features,
            target_role=target_role,
            is_intern=is_intern,
            github_data=github_data,
            linkedin_data=linkedin_data,
        )
    except Exception as exc:  # noqa: BLE001
        if warn_sink is not None:
            warn_sink.append(f"LLM analysis failed; used heuristic fallback: {exc}")
        return _heuristic_analysis(features, target_role, is_intern)
