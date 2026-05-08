from __future__ import annotations

from typing import Dict

from app.scoring.weights import SCORING_WEIGHTS

_GITHUB_SKILLS_KEYS = ("github_activity", "project_quality", "skills")


def _effective_weights(linkedin_placeholder: bool) -> Dict[str, float]:
    base = dict(SCORING_WEIGHTS)
    if not linkedin_placeholder:
        return base
    spare = base["experience"] + base["achievements"]
    base["experience"] = 0.0
    base["achievements"] = 0.0
    trio_sum = sum(base[k] for k in _GITHUB_SKILLS_KEYS)
    if trio_sum <= 0:
        return base
    for k in _GITHUB_SKILLS_KEYS:
        base[k] += spare * (SCORING_WEIGHTS[k] / trio_sum)
    return base


def compute_weighted_score(
    category_scores: Dict[str, float],
    *,
    linkedin_placeholder: bool = False,
) -> Dict[str, object]:
    weights = _effective_weights(linkedin_placeholder)
    weighted_sum = 0.0
    breakdown: Dict[str, object] = {}

    for key, weight in weights.items():
        score = float(category_scores.get(key, 0.0))
        contribution = score * weight
        weighted_sum += contribution
        breakdown[key] = {
            "score": round(score, 2),
            "weight": round(weight, 4),
            "weighted_contribution": round(contribution, 2),
        }

    return {
        "final_score": round(max(0.0, min(100.0, weighted_sum)), 2),
        "category_breakdown": breakdown,
        "scoring_mode": "github_emphasis" if linkedin_placeholder else "full_profile",
    }
