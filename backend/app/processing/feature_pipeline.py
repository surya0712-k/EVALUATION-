from __future__ import annotations

from typing import Any, Dict


def _cap_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def build_features(github_data: Dict[str, Any], linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
    repo_count = github_data.get("repo_count", 0)
    total_stars = github_data.get("total_stars", 0)
    total_forks = github_data.get("total_forks", 0)
    commit_activity_90d = github_data.get("commit_activity_90d", 0)
    languages = github_data.get("languages", [])

    tech_depth_score = _cap_100((len(languages) * 10) + (total_stars * 0.6) + (repo_count * 1.2))
    consistency_score = _cap_100(commit_activity_90d * 1.5)
    open_source_contribution_signal = _cap_100((total_forks * 1.1) + (total_stars * 0.4))

    # Public "events" in 90d often read as 0 even for strong profiles (pagination, event types).
    # Blend repo + star/fork signal so github_activity is not stuck near repo_count*0.6 alone.
    events_activity = (commit_activity_90d * 1.5) + (repo_count * 0.6)
    readme_signal = float(github_data.get("readme_signal", 0) or 0)
    stars_repo_signal = min(
        82.0,
        repo_count * 1.85
        + min(float(total_stars), 3500.0) * 0.017
        + min(float(total_forks), 1200.0) * 0.028
        + min(10.0, readme_signal * 0.12),
    )
    github_activity = _cap_100(max(events_activity, stars_repo_signal))
    project_quality = _cap_100((total_stars * 0.8) + (total_forks * 0.6) + (tech_depth_score * 0.2))
    skills = _cap_100((len(languages) * 8) + linkedin_data.get("skill_relevance_score", 40) * 0.4)
    experience = _cap_100((linkedin_data.get("experience_years", 0) * 8) + linkedin_data.get("career_progression_score", 40) * 0.3)
    achievements = _cap_100((len(linkedin_data.get("achievements", [])) * 12) + open_source_contribution_signal * 0.3)

    return {
        "tech_depth_score": tech_depth_score,
        "consistency_score": consistency_score,
        "open_source_contribution_signal": open_source_contribution_signal,
        "category_scores": {
            "github_activity": github_activity,
            "project_quality": project_quality,
            "skills": skills,
            "experience": experience,
            "achievements": achievements,
        },
        "data_completeness": (linkedin_data.get("data_completeness", 0.2) + 1.0) / 2.0,
    }
