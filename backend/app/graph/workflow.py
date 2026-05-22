from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.analysis.llm_reasoner import analyze_candidate
from app.analyzers.github import analyze_github_profile, build_github_analysis
from app.analyzers.linkedin import analyze_linkedin_profile, build_linkedin_analysis
from app.graph.state import EvaluationState
from app.processing.feature_pipeline import build_features
from app.scoring.engine import compute_weighted_score


def fetch_data_node(state: EvaluationState) -> EvaluationState:
    warnings = list(state.get("warnings", []))
    github_data: Dict[str, Any] = {}
    linkedin_data: Dict[str, Any] = {}

    try:
        gh = analyze_github_profile(state["github_url"])
        github_data = gh.get("raw", {}) or {}
        warnings.extend(gh.get("analysis", {}).get("warnings", []))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"GitHub fetch issue: {exc}")

    try:
        li = analyze_linkedin_profile(
            state["linkedin_url"],
            experience_years=state.get("linkedin_experience_years"),
            achievements=state.get("linkedin_achievements"),
            skills=state.get("linkedin_skills"),
        )
        linkedin_data = li.get("raw", {}) or {}
        warnings.extend(li.get("analysis", {}).get("warnings", []))
        if linkedin_data.get("data_source") == "placeholder" and li.get("debug"):
            apify_fail = next(
                (
                    a.get("reason")
                    for a in li["debug"].get("attempts", [])
                    if a.get("provider") == "apify" and a.get("status") == "failed"
                ),
                None,
            )
            if apify_fail and not any("Apify detail:" in w for w in warnings):
                warnings.append(f"Apify detail: {apify_fail}")
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
    github_data = state.get("github_data", {}) or {}
    linkedin_data = state.get("linkedin_data", {}) or {}
    linkedin_url = str(state.get("linkedin_url", "")).strip()
    gh_analysis = build_github_analysis(github_data) if github_data else {}
    li_analysis = (
        build_linkedin_analysis(linkedin_url, linkedin_data) if linkedin_data else {}
    )

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
            "career_progression_score": linkedin_data.get("career_progression_score", 0),
            "skill_relevance_score": linkedin_data.get("skill_relevance_score", 0),
        },
        "intern_criteria": state["llm_analysis"].get("intern_criteria", {}),
        "data_completeness": state["processed_features"]["data_completeness"],
        "scoring_mode": state["scoring"].get("scoring_mode", "full_profile"),
        "github_signals": gh_analysis.get("github_signals", {}),
        "linkedin_signals": li_analysis.get("linkedin_signals", {}),
        "profile_highlights": {
            "github": gh_analysis.get("highlights", []),
            "linkedin": li_analysis.get("highlights", []),
        },
        "linkedin_enrichment_tier": li_analysis.get("enrichment_tier"),
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
