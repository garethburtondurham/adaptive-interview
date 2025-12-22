"""
Director Agent - Manages session constraints and decides when to end.
"""
from typing import Dict, Any
from datetime import datetime

from state import InterviewState

# Maximum interview duration in minutes
MAX_DURATION_MINUTES = 30
# Maximum number of questions
MAX_QUESTIONS = 10


def director_node(state: InterviewState) -> Dict[str, Any]:
    """
    Manages session constraints and decides when to end.
    """
    # Check if already complete
    if state.get("is_complete"):
        return {"should_continue": False}

    # Check question limit
    if state["current_question_index"] >= len(state["question_sequence"]):
        return {
            "should_continue": False,
            "is_complete": True,
        }

    # Check if we've exceeded max questions
    if len(state["question_scores"]) >= MAX_QUESTIONS:
        return {
            "should_continue": False,
            "is_complete": True,
        }

    # Check time limit
    started_at = datetime.fromisoformat(state["started_at"])
    elapsed_minutes = (datetime.utcnow() - started_at).total_seconds() / 60

    if elapsed_minutes >= MAX_DURATION_MINUTES:
        return {
            "should_continue": False,
            "is_complete": True,
        }

    # Continue the interview
    return {"should_continue": True}


def should_continue(state: InterviewState) -> str:
    """
    Conditional edge function for LangGraph.
    Returns the next node to route to.
    """
    if state.get("is_complete") or not state.get("should_continue", True):
        return "end"
    return "continue"
