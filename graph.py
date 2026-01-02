"""
LangGraph construction for the Adaptive Case Interview System.

New Flow (Evaluator-Driven):
1. Candidate responds
2. Evaluator assesses and provides guidance
3. Interviewer responds following evaluator guidance
4. Manager checks constraints and provides guidance

This module now supports multiple interview types via the InterviewSpec system.
The InterviewRunner can be initialized with either:
- A legacy InterviewState (backward compatible)
- An InterviewSpec (new context injection approach)
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid

from state import (
    InterviewState,
    Message,
    Phase,
    initialize_competency_scores,
    has_spec,
    get_spec_interview_type,
)
from agents.evaluator import evaluator_node
from agents.interviewer import interviewer_node, generate_closing_message
from agents.manager import manager_node


def initialize_from_spec(
    spec: Union[Dict[str, Any], "InterviewSpec"],
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewState:
    """
    Initialize an InterviewState from an InterviewSpec.

    This function bridges the spec system to the state system, creating
    a properly initialized state ready for the interview flow.

    Args:
        spec: An InterviewSpec (or dict representation)
        candidate_id: Optional identifier for the candidate
        session_id: Optional session ID (generated if not provided)

    Returns:
        Fully initialized InterviewState
    """
    # Handle Pydantic model
    if hasattr(spec, "model_dump"):
        spec_dict = spec.model_dump()
    else:
        spec_dict = spec

    # Generate session ID if not provided
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"

    # Determine initial phase from spec
    phases = spec_dict.get("phases", [])
    initial_phase = phases[0]["id"].upper() if phases else "OPENING"

    # Initialize competency scores from spec
    competency_scores = initialize_competency_scores(spec_dict)

    # Extract legacy case fields if this is a case interview
    context_packet = spec_dict.get("context_packet", {})
    case_study = context_packet.get("case_study") or {}

    # Build the state
    state: InterviewState = {
        # Session metadata
        "session_id": session_id,
        "candidate_id": candidate_id,
        "started_at": datetime.utcnow().isoformat(),

        # Interview specification (NEW)
        "interview_spec": spec_dict,

        # Legacy case fields (populated for case interviews, empty otherwise)
        "case_id": spec_dict.get("spec_id", ""),
        "case_title": spec_dict.get("title", ""),
        "opening": case_study.get("case_prompt", ""),
        "facts": case_study.get("facts", {}),
        "root_cause": case_study.get("root_cause", ""),
        "strong_recommendations": case_study.get("strong_recommendations", []),
        "calibration": case_study.get("calibration_examples", {}),
        "case_red_flags": [],
        "case_green_flags": [],

        # Current position
        "current_phase": initial_phase,

        # Conversation
        "messages": [],

        # Multi-competency scoring (NEW)
        "competency_scores": competency_scores,

        # Legacy single-score tracking
        "current_level": 0,
        "level_name": "NOT_ASSESSED",
        "level_trend": "STABLE",
        "level_history": [],
        "red_flags_observed": [],
        "green_flags_observed": [],

        # Evaluator guidance
        "evaluator_action": "",
        "evaluator_guidance": "",
        "data_to_share": None,

        # Manager directive (NEW)
        "manager_directive": None,

        # Legacy scoring
        "question_scores": [],

        # Control
        "is_complete": False,
        "final_score": None,
        "final_summary": None,

        # Usage
        "total_tokens": 0,
    }

    return state


class InterviewRunner:
    """
    High-level interface for running interviews.

    Supports two initialization patterns:
    1. Legacy: InterviewRunner(initial_state) - for backward compatibility
    2. New: InterviewRunner.from_spec(spec) - for context injection approach

    Flow:
    1. Evaluator assesses candidate and provides guidance (runs FIRST)
    2. Interviewer responds following evaluator guidance
    3. Manager checks constraints and provides guidance
    """

    def __init__(self, initial_state: InterviewState):
        self.state = initial_state
        self.response_count = 0

    @classmethod
    def from_spec(
        cls,
        spec: Union[Dict[str, Any], "InterviewSpec"],
        candidate_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "InterviewRunner":
        """
        Create an InterviewRunner from an InterviewSpec.

        This is the preferred method for creating new interviews using
        the context injection architecture.

        Args:
            spec: An InterviewSpec or dict representation
            candidate_id: Optional candidate identifier
            session_id: Optional session identifier

        Returns:
            Configured InterviewRunner ready to start
        """
        state = initialize_from_spec(spec, candidate_id, session_id)
        return cls(state)

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

        # 3. Run manager to check constraints and provide guidance
        manager_result = manager_node(self.state)
        self.state = {**self.state, **manager_result}

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

    # =========================================================================
    # NEW: Spec-based methods
    # =========================================================================

    def get_interview_type(self) -> Optional[str]:
        """Get the interview type from the spec."""
        return get_spec_interview_type(self.state)

    def has_spec(self) -> bool:
        """Check if this interview uses the new spec system."""
        return has_spec(self.state)

    def get_competency_scores(self) -> Dict[str, Any]:
        """
        Get all competency scores.

        Returns:
            Dictionary mapping competency_id to CompetencyScore
        """
        return self.state.get("competency_scores", {})

    def get_competency_summary(self) -> Dict[str, Any]:
        """
        Get a summary of competency assessments.

        Returns dict with:
            - assessed: List of competencies with scores
            - pending: List of competencies not yet assessed
            - critical_status: Pass/fail status on critical competencies
        """
        scores = self.state.get("competency_scores", {})
        spec = self.state.get("interview_spec", {})

        # Get tiers from spec
        competency_tiers = {}
        for comp in spec.get("competencies", []):
            comp_id = comp.get("competency_id", comp.get("id"))
            competency_tiers[comp_id] = comp.get("tier", "important")

        assessed = []
        pending = []
        critical_status = "passing"

        for comp_id, score in scores.items():
            level = score.get("current_level", 0)
            tier = competency_tiers.get(comp_id, "important")

            if level == 0:
                pending.append(comp_id)
            else:
                assessed.append({
                    "id": comp_id,
                    "level": level,
                    "tier": tier,
                    "confidence": score.get("confidence", "low")
                })

                # Check critical competencies
                if tier == "critical" and level < 3:
                    critical_status = "failing"

        return {
            "assessed": assessed,
            "pending": pending,
            "critical_status": critical_status
        }

    def get_manager_directive(self) -> Optional[Dict[str, Any]]:
        """Get the current manager directive."""
        return self.state.get("manager_directive")

    def get_current_phase(self) -> str:
        """Get the current phase ID."""
        return self.state.get("current_phase", "UNKNOWN")

    def get_spec(self) -> Optional[Dict[str, Any]]:
        """Get the interview spec if present."""
        return self.state.get("interview_spec")
