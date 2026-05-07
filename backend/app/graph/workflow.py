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

    try:
        github_data = github_collector.collect(state["github_url"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"GitHub fetch issue: {exc}")

    try:
        linkedin_data = linkedin_collector.collect(state["linkedin_url"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"LinkedIn fetch issue: {exc}")

    return {
        **state,
        "github_data": github_data,
        "linkedin_data": linkedin_data,
        "warnings": warnings,
    }


def processing_node(state: EvaluationState) -> EvaluationState:
    processed = build_features(
        state.get("github_data", {}),
        state.get("linkedin_data", {}),
    )
    return {**state, "processed_features": processed}


def llm_analysis_node(state: EvaluationState) -> EvaluationState:
    llm_analysis = analyze_candidate(
        features=state["processed_features"],
        target_role=state.get("target_role", "Software Engineer"),
        is_intern=state.get("is_intern", False),
    )
    return {**state, "llm_analysis": llm_analysis}


def scoring_node(state: EvaluationState) -> EvaluationState:
    scoring = compute_weighted_score(state["processed_features"]["category_scores"])
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
        "warnings": state.get("warnings", []),
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
