from __future__ import annotations

from typing import Any, Dict


class LinkedInCollector:
    """
    Placeholder adapter for PhantomBuster or similar scraping tools.
    Replace `collect` internals with actual provider API calls.
    """

    def collect(self, linkedin_url: str) -> Dict[str, Any]:
        # MVP fallback: return a sparse structure so pipeline still runs.
        return {
            "linkedin_url": linkedin_url,
            "experience_years": 0,
            "skills": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "career_progression_score": 40,
            "skill_relevance_score": 40,
            "data_source": "placeholder",
            "data_completeness": 0.2,
        }
