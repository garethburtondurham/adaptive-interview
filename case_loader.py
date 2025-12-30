"""
Case loading and initialization utilities.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
import uuid
from datetime import datetime

from state import InterviewState

CASES_DIR = Path(__file__).parent / "cases"


def load_case(case_id: str) -> Dict[str, Any]:
    """Load a case definition from JSON file."""
    case_path = CASES_DIR / f"{case_id}.json"
    if not case_path.exists():
        raise FileNotFoundError(f"Case not found: {case_id}")

    with open(case_path, "r", encoding="utf-8") as f:
        return json.load(f)


def initialize_interview_state(
    case_id: str, candidate_id: str = None
) -> InterviewState:
    """Create a fresh interview state from a case definition."""
    case = load_case(case_id)

    return InterviewState(
        # Session metadata
        session_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        case_id=case_id,
        started_at=datetime.utcnow().isoformat(),

        # Case content - new structure
        case_title=case["title"],
        opening=case["opening"],
        facts=case["facts"],
        root_cause=case.get("root_cause", ""),
        strong_recommendations=case.get("strong_recommendations", []),
        calibration=case.get("calibration", {}),
        case_red_flags=case.get("red_flags", []),
        case_green_flags=case.get("green_flags", []),

        # Current position
        current_phase="INTRO",

        # Conversation tracking
        messages=[],

        # Performance tracking
        current_level=0,  # Not yet assessed
        level_name="NOT_ASSESSED",
        level_trend="STABLE",
        level_history=[],
        red_flags_observed=[],
        green_flags_observed=[],

        # Evaluator guidance (set by evaluator, used by interviewer)
        evaluator_action="",
        evaluator_guidance="",
        data_to_share=None,

        # Scoring
        question_scores=[],

        # Control
        is_complete=False,
        final_score=None,
        final_summary=None,

        # Usage tracking
        total_tokens=0,
    )


def get_case_data(state: InterviewState) -> Dict[str, Any]:
    """
    Build the case data dictionary for the interviewer prompt.
    This extracts the case-specific content from state.
    """
    return {
        "title": state["case_title"],
        "opening": state["opening"],
        "facts": state["facts"],
        "root_cause": state["root_cause"],
        "strong_recommendations": state["strong_recommendations"],
        "calibration": state["calibration"],
        "red_flags": state["case_red_flags"],
        "green_flags": state["case_green_flags"],
    }


def get_available_cases() -> List[str]:
    """List all available case IDs."""
    return [f.stem for f in CASES_DIR.glob("*.json")]
