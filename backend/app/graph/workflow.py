from __future__ import annotations

import os
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.analysis.llm_reasoner import analyze_candidate
from app.collectors.github_api import GitHubAPICollector
from app.collectors.linkedin_phantombuster import LinkedInCollector
from app.graph.state import EvaluationState
from app.processing.feature_pipeline import build_features
from app.scoring.engine import compute_weighted_score


def fetch_data_node(state: EvaluationState) -> EvaluationState:
    warnings = state.get("warnings", [])

    github_token = os.getenv("GITHUB_TOKEN")
    github_collector = GitHubAPICollector(token=github_token)
    linkedin_collector = LinkedInCollector()

    github_data: Dict[str, Any] = {}
    linkedin_data: Dict[str, Any] = {}
    linkedin_debug: Dict[str, Any] = {}

    try:
        github_data = github_collector.collect(state["github_url"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"GitHub fetch issue: {exc}")

    if github_data and int(github_data.get("repo_count") or 0) > 0:
        if int(github_data.get("commit_activity_90d") or 0) == 0:
            warnings.append(
                "No public GitHub pushes detected in the last 90 days for this username. "
                "Work on private repos, unpushed commits, or commits under another account "
                "will not appear in this score."
            )

    try:
        linkedin_data, linkedin_debug = linkedin_collector.collect_with_debug(state["linkedin_url"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"LinkedIn fetch issue: {exc}")
        linkedin_debug = {"attempts": [{"provider": "collector", "status": "error", "reason": str(exc)}]}

    exp_override = state.get("linkedin_experience_years")
    if exp_override is not None:
        try:
            linkedin_data["experience_years"] = float(exp_override)
        except (TypeError, ValueError):
            pass
    ach_override = state.get("linkedin_achievements")
    if isinstance(ach_override, list) and ach_override:
        linkedin_data["achievements"] = [str(x).strip() for x in ach_override if str(x).strip()]
    skills_override = state.get("linkedin_skills")
    if isinstance(skills_override, list) and skills_override:
        linkedin_data["skills"] = [str(x).strip() for x in skills_override if str(x).strip()]

    if (
        exp_override is not None
        or (isinstance(ach_override, list) and ach_override)
        or (isinstance(skills_override, list) and skills_override)
    ):
        linkedin_data["data_source"] = "user_supplied"
        linkedin_data["data_completeness"] = max(
            float(linkedin_data.get("data_completeness", 0.2)),
            0.72,
        )
        linkedin_data["career_progression_score"] = max(
            float(linkedin_data.get("career_progression_score", 40)),
            52.0,
        )
        linkedin_data["skill_relevance_score"] = max(
            float(linkedin_data.get("skill_relevance_score", 40)),
            52.0,
        )

    if linkedin_data.get("data_source") == "placeholder":
        linkedin_url = str(state.get("linkedin_url", "")).strip()
        if linkedin_url.endswith("/in") or linkedin_url.endswith("/in/"):
            warnings.append(
                "LinkedIn URL looks incomplete (it ends at /in/). Use a full profile URL like "
                "https://www.linkedin.com/in/<username>/."
            )
        warnings.append(
            "LinkedIn was not enriched: configure Apify (APIFY_API_TOKEN) for automated scraping, "
            "or use backend/linkedin_profile.json / LINKEDIN_PROFILE_JSON. "
            "Until then, scores use GitHub-heavy weighting."
        )

    return {
        **state,
        "github_data": github_data,
        "linkedin_data": linkedin_data,
        "linkedin_debug": linkedin_debug,
        "warnings": warnings,
    }


def processing_node(state: EvaluationState) -> EvaluationState:
    processed = build_features(
        state.get("github_data", {}),
        state.get("linkedin_data", {}),
    )
    return {**state, "processed_features": processed}


def llm_analysis_node(state: EvaluationState) -> EvaluationState:
    warn_extra: list[str] = []
    llm_analysis = analyze_candidate(
        features=state["processed_features"],
        target_role=state.get("target_role", "Software Engineer"),
        is_intern=state.get("is_intern", False),
        github_data=state.get("github_data", {}),
        linkedin_data=state.get("linkedin_data", {}),
        warn_sink=warn_extra,
    )
    warnings = [*state.get("warnings", []), *warn_extra]
    return {**state, "llm_analysis": llm_analysis, "warnings": warnings}


def scoring_node(state: EvaluationState) -> EvaluationState:
    linkedin_placeholder = state.get("linkedin_data", {}).get("data_source") == "placeholder"
    scoring = compute_weighted_score(
        state["processed_features"]["category_scores"],
        linkedin_placeholder=linkedin_placeholder,
    )
    return {**state, "scoring": scoring}


def output_node(state: EvaluationState) -> EvaluationState:
    output = {
        "final_score": state["scoring"]["final_score"],
        "category_breakdown": state["scoring"]["category_breakdown"],
        "strengths": state["llm_analysis"]["strengths"],
        "weaknesses": state["llm_analysis"]["weaknesses"],
        "hiring_recommendations": state["llm_analysis"]["hiring_recommendations"],
        "suggested_role_fit": state["llm_analysis"]["suggested_role_fit"],
        "generated_signals": {
            "tech_depth_score": state["processed_features"]["tech_depth_score"],
            "consistency_score": state["processed_features"]["consistency_score"],
            "open_source_contribution_signal": state["processed_features"][
                "open_source_contribution_signal"
            ],
            "career_progression_score": state.get("linkedin_data", {}).get(
                "career_progression_score", 0
            ),
            "skill_relevance_score": state.get("linkedin_data", {}).get(
                "skill_relevance_score", 0
            ),
        },
        "intern_criteria": state["llm_analysis"].get("intern_criteria", {}),
        "data_completeness": state["processed_features"]["data_completeness"],
        "scoring_mode": state["scoring"].get("scoring_mode", "full_profile"),
        "github_signals": {
            "commit_activity_index_90d": state.get("github_data", {}).get("commit_activity_90d"),
            "repos_pushed_90d": state.get("github_data", {}).get("repos_pushed_90d"),
            "public_push_commits_estimated_90d": state.get("github_data", {}).get("push_commits_90d"),
            "commits_repo_scan_90d": state.get("github_data", {}).get("commits_repo_scan_90d"),
            "public_repo_count": state.get("github_data", {}).get("repo_count"),
        },
        "warnings": state.get("warnings", []),
        "linkedin_data_source": state.get("linkedin_data", {}).get("data_source", "unknown"),
        "linkedin_debug": state.get("linkedin_debug", {}),
    }
    return {**state, "output": output}


def build_workflow():
    graph = StateGraph(EvaluationState)
    graph.add_node("data_fetch", fetch_data_node)
    graph.add_node("processing", processing_node)
    graph.add_node("llm_analysis", llm_analysis_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("output", output_node)

    graph.set_entry_point("data_fetch")
    graph.add_edge("data_fetch", "processing")
    graph.add_edge("processing", "llm_analysis")
    graph.add_edge("llm_analysis", "scoring")
    graph.add_edge("scoring", "output")
    graph.add_edge("output", END)

    return graph.compile()
