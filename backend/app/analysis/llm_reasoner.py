from __future__ import annotations

from typing import Any, Dict, List


def analyze_candidate(features: Dict[str, Any], target_role: str, is_intern: bool) -> Dict[str, Any]:
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

    intern_criteria = {}
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
