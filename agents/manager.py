"""
Manager Agent - Session orchestration and competency coverage.

The Manager (formerly Director) has a simplified, advisory role:
- Checks hard constraints (time, exchanges)
- Monitors competency coverage - which competencies need more signal
- Suggests phase transitions (fluid, not enforced)
- Provides focus guidance to the interviewer

The Manager does NOT decide interview type (pre-set in spec) or
make assessment judgments (that's the evaluator's job).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from state import (
    InterviewState,
    ManagerDirective,
    has_spec,
    get_current_phase_config,
    get_heuristics,
)


def manager_node(state: InterviewState) -> Dict[str, Any]:
    """
    Manage session constraints and provide guidance for interview flow.

    Returns:
        Dictionary with:
        - should_continue: Whether the interview should continue
        - is_complete: Whether to mark the interview as complete
        - manager_directive: Guidance for the interviewer
    """
    # Check if already complete
    if state.get("is_complete"):
        return {"should_continue": False}

    # Get constraints from spec or use defaults
    if has_spec(state):
        spec = state.get("interview_spec", {})
        constraints = spec.get("constraints", {})
        max_duration = constraints.get("max_duration_minutes", 30)
        max_exchanges = constraints.get("max_exchanges", 15)
        min_exchanges = constraints.get("min_exchanges_for_completion", 5)
        allow_early = constraints.get("allow_early_termination", True)
    else:
        max_duration = 30
        max_exchanges = 15
        min_exchanges = 5
        allow_early = True

    # Count candidate exchanges
    candidate_messages = [m for m in state.get("messages", []) if m["role"] == "candidate"]
    num_exchanges = len(candidate_messages)

    # Check time elapsed
    started_at = datetime.fromisoformat(state["started_at"])
    elapsed_minutes = (datetime.utcnow() - started_at).total_seconds() / 60

    # Determine urgency
    time_remaining = max_duration - elapsed_minutes
    exchanges_remaining = max_exchanges - num_exchanges

    if time_remaining <= 3 or exchanges_remaining <= 2:
        urgency = "must_end"
    elif time_remaining <= 8 or exchanges_remaining <= 4:
        urgency = "wrap_up_soon"
    else:
        urgency = "normal"

    # Check hard termination conditions
    if num_exchanges >= max_exchanges:
        return {
            "should_continue": False,
            "is_complete": True,
            "manager_directive": _create_directive(
                should_continue=False,
                urgency="must_end",
                focus_area="Maximum exchanges reached"
            )
        }

    if elapsed_minutes >= max_duration:
        return {
            "should_continue": False,
            "is_complete": True,
            "manager_directive": _create_directive(
                should_continue=False,
                urgency="must_end",
                focus_area="Time limit reached"
            )
        }

    # For spec-driven interviews, check competency coverage and phase guidance
    if has_spec(state):
        directive = _build_spec_directive(state, num_exchanges, min_exchanges, urgency, allow_early)
    else:
        directive = _build_legacy_directive(state, num_exchanges, min_exchanges, urgency)

    # Check if we should end based on directive
    if not directive.get("should_continue", True):
        return {
            "should_continue": False,
            "is_complete": True,
            "manager_directive": directive
        }

    return {
        "should_continue": True,
        "manager_directive": directive
    }


def _build_spec_directive(
    state: InterviewState,
    num_exchanges: int,
    min_exchanges: int,
    urgency: str,
    allow_early: bool
) -> ManagerDirective:
    """Build directive for spec-driven interviews."""

    spec = state.get("interview_spec", {})
    competency_scores = state.get("competency_scores", {})

    # Analyze competency coverage
    undercovered = []
    satisfied = []

    for comp_config in spec.get("competencies", []):
        comp_id = comp_config.get("competency_id", "")
        tier = comp_config.get("tier", "important")

        score = competency_scores.get(comp_id, {})
        level = score.get("current_level", 0)
        confidence = score.get("confidence", "low")

        # Determine if we have enough signal
        if level == 0:
            # Not yet assessed
            undercovered.append(comp_id)
        elif confidence == "low":
            # Assessed but low confidence
            undercovered.append(comp_id)
        elif tier == "critical" and level < 3:
            # Critical competency below passing - need more signal to confirm
            undercovered.append(comp_id)
        else:
            satisfied.append(comp_id)

    # Determine focus area
    focus_area = None
    if undercovered:
        # Prioritize critical competencies
        critical_undercovered = [
            c for c in undercovered
            if _get_tier(c, spec) == "critical"
        ]
        if critical_undercovered:
            focus_area = f"Need more signal on: {', '.join(critical_undercovered[:2])}"
        else:
            focus_area = f"Explore: {undercovered[0]}"

    # Check phase transition
    suggested_phase, phase_reason = _check_phase_transition(state, num_exchanges)

    # Check if interview can end early
    should_continue = True
    if allow_early and num_exchanges >= min_exchanges:
        # Can end if all competencies have sufficient signal
        all_assessed = all(
            competency_scores.get(c.get("competency_id", ""), {}).get("current_level", 0) > 0
            for c in spec.get("competencies", [])
        )
        all_confident = all(
            competency_scores.get(c.get("competency_id", ""), {}).get("confidence", "low") != "low"
            for c in spec.get("competencies", [])
        )

        if all_assessed and all_confident and not undercovered:
            # Suggest wrapping up
            if urgency == "normal":
                urgency = "wrap_up_soon"
            focus_area = "All competencies assessed - consider moving to close"

    return _create_directive(
        should_continue=should_continue,
        focus_area=focus_area,
        urgency=urgency,
        undercovered_competencies=undercovered,
        satisfied_competencies=satisfied,
        suggested_phase=suggested_phase,
        phase_suggestion_reason=phase_reason
    )


def _build_legacy_directive(
    state: InterviewState,
    num_exchanges: int,
    min_exchanges: int,
    urgency: str
) -> ManagerDirective:
    """Build directive for legacy case interviews."""

    current_phase = state.get("current_phase", "STRUCTURING")

    # Check if in synthesis with enough exchanges
    if current_phase == "SYNTHESIS" and num_exchanges >= min_exchanges:
        return _create_directive(
            should_continue=False,
            urgency="must_end",
            focus_area="Synthesis complete"
        )

    # Suggest phase based on exchange count
    suggested_phase = None
    phase_reason = None

    if current_phase == "STRUCTURING" and num_exchanges >= 3:
        suggested_phase = "ANALYSIS"
        phase_reason = "Candidate has had time to structure, consider moving to analysis"
    elif current_phase == "ANALYSIS" and num_exchanges >= 8:
        suggested_phase = "SYNTHESIS"
        phase_reason = "Analysis phase extended, consider moving to synthesis"

    return _create_directive(
        should_continue=True,
        focus_area=None,
        urgency=urgency,
        suggested_phase=suggested_phase,
        phase_suggestion_reason=phase_reason
    )


def _check_phase_transition(state: InterviewState, num_exchanges: int) -> tuple:
    """Check if a phase transition should be suggested."""

    current_phase_id = state.get("current_phase", "").lower()
    spec = state.get("interview_spec", {})
    phases = spec.get("phases", [])

    if not phases:
        return None, None

    # Find current phase config
    current_phase_config = None
    current_phase_index = -1
    for i, phase in enumerate(phases):
        if phase.get("id", "").lower() == current_phase_id:
            current_phase_config = phase
            current_phase_index = i
            break

    if not current_phase_config:
        return None, None

    # Count exchanges in current phase (simplified - count from last phase change)
    # In a full implementation, we'd track phase entry time
    phase_exchanges = num_exchanges  # Simplified for now

    # Check suggested max
    suggested_max = current_phase_config.get("suggested_max_exchanges")
    if suggested_max and phase_exchanges >= suggested_max:
        # Suggest moving to next phase
        if current_phase_index + 1 < len(phases):
            next_phase = phases[current_phase_index + 1]
            return (
                next_phase.get("id"),
                f"Current phase ({current_phase_config.get('name', '')}) has reached suggested duration"
            )

    return None, None


def _get_tier(competency_id: str, spec: Dict[str, Any]) -> str:
    """Get the tier of a competency from the spec."""
    for comp in spec.get("competencies", []):
        if comp.get("competency_id", "") == competency_id:
            return comp.get("tier", "important")
    return "important"


def _create_directive(
    should_continue: bool,
    urgency: str = "normal",
    focus_area: Optional[str] = None,
    undercovered_competencies: List[str] = None,
    satisfied_competencies: List[str] = None,
    suggested_phase: Optional[str] = None,
    phase_suggestion_reason: Optional[str] = None
) -> ManagerDirective:
    """Create a ManagerDirective."""
    return ManagerDirective(
        should_continue=should_continue,
        focus_area=focus_area,
        urgency=urgency,
        undercovered_competencies=undercovered_competencies or [],
        satisfied_competencies=satisfied_competencies or [],
        suggested_phase=suggested_phase,
        phase_suggestion_reason=phase_suggestion_reason
    )


def should_continue(state: InterviewState) -> str:
    """
    Conditional edge function for LangGraph.
    Returns the next node to route to.
    """
    if state.get("is_complete") or not state.get("should_continue", True):
        return "end"
    return "continue"


# Backward compatibility alias
director_node = manager_node
