from __future__ import annotations

from typing import Dict

from app.scoring.weights import SCORING_WEIGHTS


def compute_weighted_score(category_scores: Dict[str, float]) -> Dict[str, object]:
    weighted_sum = 0.0
    breakdown = {}

    for key, weight in SCORING_WEIGHTS.items():
        score = float(category_scores.get(key, 0.0))
        contribution = score * weight
        weighted_sum += contribution
        breakdown[key] = {
            "score": round(score, 2),
            "weight": weight,
            "weighted_contribution": round(contribution, 2),
        }

    return {
        "final_score": round(max(0.0, min(100.0, weighted_sum)), 2),
        "category_breakdown": breakdown,
    }
