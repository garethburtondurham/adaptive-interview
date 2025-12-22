"""
Director Agent - Manages session constraints and decides when to end.
"""
from typing import Dict, Any
from datetime import datetime

from state import InterviewState

# Maximum interview duration in minutes
MAX_DURATION_MINUTES = 30
# Minimum areas to explore before ending
MIN_AREAS_TO_COVER = 3
# Maximum number of exchanges (candidate responses)
MAX_EXCHANGES = 15


def director_node(state: InterviewState) -> Dict[str, Any]:
    """
    Manages session constraints and decides when to end the interview.

    Ends the interview when:
    1. Already marked complete
    2. Time limit exceeded
    3. Maximum exchanges reached
    4. Most exploration areas covered and in synthesis phase
    """
    # Check if already complete
    if state.get("is_complete"):
        return {"should_continue": False}

    # Count candidate exchanges
    candidate_messages = [m for m in state.get("messages", []) if m["role"] == "candidate"]
    num_exchanges = len(candidate_messages)

    # Check if we've exceeded max exchanges
    if num_exchanges >= MAX_EXCHANGES:
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

    # Check if enough areas have been explored and we're in synthesis
    areas_explored = len(state.get("areas_explored", []))
    total_areas = len(state.get("exploration_areas", []))
    current_phase = state.get("current_phase", "STRUCTURING")

    # End if we've covered most areas and reached synthesis
    if areas_explored >= min(MIN_AREAS_TO_COVER, total_areas) and current_phase == "SYNTHESIS":
        # Check if we've had at least a few synthesis exchanges
        if num_exchanges >= 5:
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
