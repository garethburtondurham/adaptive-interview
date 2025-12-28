"""
Director Agent - Manages session constraints and decides when to end.
"""
from typing import Dict, Any
from datetime import datetime

from state import InterviewState

# Maximum interview duration in minutes
MAX_DURATION_MINUTES = 30
# Maximum number of exchanges (candidate responses)
MAX_EXCHANGES = 15
# Minimum exchanges before allowing synthesis-based end
MIN_EXCHANGES_FOR_SYNTHESIS = 5


def director_node(state: InterviewState) -> Dict[str, Any]:
    """
    Manages session constraints and decides when to end the interview.

    Ends the interview when:
    1. Already marked complete
    2. Time limit exceeded
    3. Maximum exchanges reached
    4. In synthesis phase with enough exchanges
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

    # Check if we're in synthesis phase with enough exchanges
    current_phase = state.get("current_phase", "STRUCTURING")
    if current_phase == "SYNTHESIS" and num_exchanges >= MIN_EXCHANGES_FOR_SYNTHESIS:
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
