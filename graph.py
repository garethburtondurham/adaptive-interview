"""
LangGraph construction for the Adaptive Case Interview System.

New Flow (Evaluator-Driven):
1. Candidate responds
2. Evaluator assesses and provides guidance
3. Interviewer responds following evaluator guidance
4. Director checks constraints
"""
from typing import Dict, Any, List
from datetime import datetime

from state import InterviewState, Message
from agents.evaluator import evaluator_node
from agents.interviewer import interviewer_node, generate_closing_message
from agents.director import director_node


class InterviewRunner:
    """
    High-level interface for running interviews.

    Flow:
    1. Evaluator assesses candidate and provides guidance (runs FIRST)
    2. Interviewer responds following evaluator guidance
    3. Director checks if interview should end
    """

    def __init__(self, initial_state: InterviewState):
        self.state = initial_state
        self.response_count = 0

    def start(self) -> str:
        """Start the interview and return the opening message."""
        # For opening, just call interviewer directly (no candidate response yet)
        result = interviewer_node(self.state)
        self.state = {**self.state, **result}
        return self._get_last_interviewer_message()

    def respond(self, candidate_response: str) -> str:
        """Process candidate's response and return interviewer's next message."""
        # Add candidate message
        candidate_message = Message(
            role="candidate",
            content=candidate_response,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.state["messages"] = self.state["messages"] + [candidate_message]
        self.response_count += 1

        # 1. Run evaluator FIRST - assess candidate and provide guidance
        evaluator_result = evaluator_node(self.state)
        self.state = {**self.state, **evaluator_result}

        # 2. Run interviewer - follows evaluator guidance
        interviewer_result = interviewer_node(self.state)
        self.state = {**self.state, **interviewer_result}

        # 3. Run director to check constraints
        director_result = director_node(self.state)
        self.state = {**self.state, **director_result}

        # Check if interview should end
        if self.state.get("is_complete"):
            if not self._last_message_is_closing():
                closing_result = generate_closing_message(self.state)
                self.state = {**self.state, **closing_result}

        return self._get_last_interviewer_message()

    def _get_last_interviewer_message(self) -> str:
        """Get the most recent interviewer message."""
        for msg in reversed(self.state["messages"]):
            if msg["role"] == "interviewer":
                return msg["content"]
        return ""

    def _last_message_is_closing(self) -> bool:
        """Check if the last message is already a closing message."""
        if not self.state["messages"]:
            return False
        last = self.state["messages"][-1]
        return last["role"] == "interviewer" and "wrap up" in last["content"].lower()

    def is_complete(self) -> bool:
        """Check if the interview is complete."""
        return self.state.get("is_complete", False)

    def get_state(self) -> InterviewState:
        """Get the current interview state."""
        return self.state

    def get_current_level(self) -> tuple:
        """Get current assessment level and name."""
        return (
            self.state.get("current_level", 0),
            self.state.get("level_name", "NOT_ASSESSED")
        )

    def get_flags(self) -> tuple:
        """Get red and green flags observed during the interview."""
        return (
            self.state.get("red_flags_observed", []),
            self.state.get("green_flags_observed", [])
        )

    def get_evaluator_guidance(self) -> tuple:
        """Get the current evaluator guidance."""
        return (
            self.state.get("evaluator_action", ""),
            self.state.get("evaluator_guidance", "")
        )

    def get_messages(self) -> List[Message]:
        """Get all conversation messages."""
        return self.state.get("messages", [])
