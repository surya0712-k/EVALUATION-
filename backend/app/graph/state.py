from typing import Any, Dict, List, TypedDict


class EvaluationState(TypedDict, total=False):
    github_url: str
    linkedin_url: str
    target_role: str
    is_intern: bool
    github_data: Dict[str, Any]
    linkedin_data: Dict[str, Any]
    processed_features: Dict[str, Any]
    llm_analysis: Dict[str, Any]
    scoring: Dict[str, Any]
    output: Dict[str, Any]
    warnings: List[str]
