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
        session_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        case_id=case_id,
        started_at=datetime.utcnow().isoformat(),
        case_title=case["title"],
        case_prompt=case["candidate_prompt"],
        hidden_facts=case["hidden_facts"],
        exploration_areas=case["exploration_areas"],
        current_phase="INTRO",
        difficulty_level=3,  # Start at medium
        messages=[],
        areas_explored=[],
        positive_signals=[],
        concerns=[],
        candidate_struggling=False,
        question_scores=[],
        last_evaluator_output=None,
        next_directive=None,
        pending_hint=None,
        pending_complexity=None,
        pending_data_reveal=None,
        is_complete=False,
        final_score=None,
        final_summary=None,
    )


def get_exploration_areas(state: InterviewState) -> list:
    """Get all exploration areas for the case."""
    return state["exploration_areas"]


def get_unexplored_areas(state: InterviewState) -> list:
    """Get exploration areas that haven't been covered yet."""
    explored = set(state.get("areas_explored", []))
    return [
        area for area in state["exploration_areas"]
        if area["id"] not in explored
    ]


def get_available_cases() -> List[str]:
    """List all available case IDs."""
    return [f.stem for f in CASES_DIR.glob("*.json")]
