"""
State definitions for the Adaptive Case Interview System.

This module defines the core state that flows through all agents.
The state now supports multiple interview types via the InterviewSpec system.
"""
from typing import TypedDict, List, Optional, Literal, Dict, Any
from enum import Enum


class Phase(str, Enum):
    """
    Interview phases. These are now dynamically defined by the InterviewSpec,
    but we keep common defaults for backward compatibility.
    """
    # Legacy case interview phases
    INTRO = "INTRO"
    STRUCTURING = "STRUCTURING"
    ANALYSIS = "ANALYSIS"
    CALCULATION = "CALCULATION"
    SYNTHESIS = "SYNTHESIS"
    COMPLETE = "COMPLETE"

    # First round phases
    RAPPORT = "RAPPORT"
    EXPERIENCE_VALIDATION = "EXPERIENCE_VALIDATION"
    GAP_EXPLORATION = "GAP_EXPLORATION"
    MOTIVATION_FIT = "MOTIVATION_FIT"
    CANDIDATE_QUESTIONS = "CANDIDATE_QUESTIONS"
    CLOSE = "CLOSE"

    # Technical phases
    PROBLEM_PRESENTATION = "PROBLEM_PRESENTATION"
    APPROACH_DISCUSSION = "APPROACH_DISCUSSION"
    IMPLEMENTATION = "IMPLEMENTATION"
    TESTING = "TESTING"
    OPTIMIZATION = "OPTIMIZATION"

    # Generic
    OPENING = "OPENING"


class Message(TypedDict):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    timestamp: str


class QuestionScore(TypedDict):
    """Legacy single-question scoring - kept for backward compatibility."""
    question_id: str
    phase: str
    score: int  # 1-5
    reasoning: str
    key_elements_detected: List[str]
    difficulty_at_time: int


class CompetencyScore(TypedDict):
    """
    Score for a single competency in the multi-dimensional assessment.

    The new evaluation system tracks each competency separately, allowing:
    - Different competencies to have different levels
    - Tiered pass/fail logic (critical vs important vs bonus)
    - Detailed evidence trail per competency
    """
    competency_id: str
    current_level: int  # 0-5 (0 = not yet assessed)
    evidence: List[str]  # Observations supporting this level
    confidence: str  # "low" | "medium" | "high"

    # History of level changes
    level_history: List[Dict[str, Any]]  # [{level, exchange, reason, timestamp}]

    # Flags observed for this specific competency
    red_flags_observed: List[str]
    green_flags_observed: List[str]


class ManagerDirective(TypedDict):
    """
    Output from the Manager agent - suggestions for the interviewer.

    The Manager (formerly Director) now provides richer guidance:
    - Which competencies need more signal
    - Phase transition suggestions (not enforcement)
    - Urgency level for time management
    """
    should_continue: bool
    focus_area: Optional[str]  # e.g., "Leadership experience needs more depth"
    urgency: str  # "normal" | "wrap_up_soon" | "must_end"

    # Competency guidance
    undercovered_competencies: List[str]  # Need more signal
    satisfied_competencies: List[str]  # Have enough signal

    # Phase suggestion (fluid, not enforced)
    suggested_phase: Optional[str]
    phase_suggestion_reason: Optional[str]


class InterviewState(TypedDict):
    """
    Complete interview state that flows through all agents.

    This state now supports multiple interview types via the interview_spec field.
    Legacy case-specific fields are kept for backward compatibility but new
    interviews should use the spec system.
    """

    # =========================================================================
    # SESSION METADATA
    # =========================================================================
    session_id: str
    candidate_id: Optional[str]
    started_at: str

    # =========================================================================
    # INTERVIEW SPECIFICATION (NEW - Context Injection)
    # =========================================================================
    # The spec defines interview type, competencies, heuristics, phases, etc.
    # When present, agents read behavior from here instead of hardcoded logic.
    interview_spec: Optional[Dict[str, Any]]  # Serialized InterviewSpec

    # =========================================================================
    # LEGACY CASE FIELDS (kept for backward compatibility)
    # =========================================================================
    # These are populated for case interviews that don't use the new spec system.
    # New interviews should use interview_spec.context_packet instead.
    case_id: str
    case_title: str
    opening: str  # The case prompt presented to candidate
    facts: dict  # All case facts (provided when earned)
    root_cause: str  # The actual answer
    strong_recommendations: List[str]  # What good recommendations look like
    calibration: dict  # Level examples for calibration
    case_red_flags: List[str]  # Red flags defined in case
    case_green_flags: List[str]  # Green flags defined in case

    # =========================================================================
    # CURRENT POSITION
    # =========================================================================
    current_phase: str  # Phase ID from spec or legacy Phase enum value

    # =========================================================================
    # CONVERSATION TRACKING
    # =========================================================================
    messages: List[Message]

    # =========================================================================
    # MULTI-COMPETENCY SCORING (NEW)
    # =========================================================================
    # Each competency is tracked separately with its own level and evidence.
    competency_scores: Dict[str, CompetencyScore]  # Keyed by competency_id

    # =========================================================================
    # LEGACY SINGLE-SCORE TRACKING (kept for backward compatibility)
    # =========================================================================
    # For case interviews, we still compute an overall level from competencies.
    current_level: int  # 1-5 assessment level (derived from competency scores)
    level_name: str  # FAIL, WEAK, GOOD_NOT_ENOUGH, CLEAR_PASS, OUTSTANDING
    level_trend: str  # UP, STABLE, DOWN
    level_history: List[dict]  # Track level changes over time
    red_flags_observed: List[str]  # All red flags observed (aggregated)
    green_flags_observed: List[str]  # All green flags observed (aggregated)

    # =========================================================================
    # EVALUATOR -> INTERVIEWER GUIDANCE
    # =========================================================================
    evaluator_action: str  # DO_NOT_HELP, MINIMAL_HELP, LIGHT_HELP, CHALLENGE, LET_SHINE
    evaluator_guidance: str  # Specific guidance for interviewer
    data_to_share: Optional[str]  # Data evaluator has approved for sharing

    # =========================================================================
    # MANAGER DIRECTIVE (NEW - formerly Director)
    # =========================================================================
    manager_directive: Optional[ManagerDirective]

    # =========================================================================
    # SCORING
    # =========================================================================
    question_scores: List[QuestionScore]  # Legacy per-question scores

    # =========================================================================
    # CONTROL
    # =========================================================================
    is_complete: bool
    final_score: Optional[float]
    final_summary: Optional[str]

    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    total_tokens: int


def create_empty_competency_score(competency_id: str) -> CompetencyScore:
    """Create an empty competency score for initialization."""
    return CompetencyScore(
        competency_id=competency_id,
        current_level=0,
        evidence=[],
        confidence="low",
        level_history=[],
        red_flags_observed=[],
        green_flags_observed=[]
    )


def initialize_competency_scores(spec: Dict[str, Any]) -> Dict[str, CompetencyScore]:
    """
    Initialize competency scores from an InterviewSpec.

    Args:
        spec: Serialized InterviewSpec dictionary

    Returns:
        Dictionary of competency_id -> CompetencyScore
    """
    scores = {}
    for comp in spec.get("competencies", []):
        comp_id = comp.get("competency_id", comp.get("id"))
        scores[comp_id] = create_empty_competency_score(comp_id)
    return scores


def get_overall_level(competency_scores: Dict[str, CompetencyScore], spec: Dict[str, Any]) -> int:
    """
    Calculate overall interview level from competency scores.

    Uses tiered logic:
    - All CRITICAL competencies must be level 3+ to pass
    - IMPORTANT competencies contribute to the overall score
    - BONUS competencies can elevate but not carry

    Returns:
        Overall level 1-5
    """
    if not competency_scores:
        return 0

    # Get competency tiers from spec
    competency_tiers = {}
    for comp in spec.get("competencies", []):
        comp_id = comp.get("competency_id", comp.get("id"))
        competency_tiers[comp_id] = comp.get("tier", "important")

    # Check critical competencies
    critical_levels = []
    important_levels = []
    bonus_levels = []

    for comp_id, score in competency_scores.items():
        tier = competency_tiers.get(comp_id, "important")
        level = score.get("current_level", 0)

        if level == 0:  # Not yet assessed
            continue

        if tier == "critical":
            critical_levels.append(level)
        elif tier == "important":
            important_levels.append(level)
        else:  # bonus
            bonus_levels.append(level)

    # If any critical competency is below 3, cap overall at 2
    if critical_levels and min(critical_levels) < 3:
        # Fail on critical = can't pass overall
        return min(2, int(sum(critical_levels) / len(critical_levels)))

    # Calculate weighted average
    all_levels = critical_levels + important_levels
    if not all_levels:
        return 0

    base_level = sum(all_levels) / len(all_levels)

    # Bonus competencies can add up to 0.5 to the average
    if bonus_levels:
        bonus_boost = (sum(bonus_levels) / len(bonus_levels) - 3) * 0.1
        base_level = min(5, base_level + max(0, bonus_boost))

    return round(base_level)


def get_level_name(level: int) -> str:
    """Convert numeric level to name."""
    names = {
        0: "NOT_ASSESSED",
        1: "FAIL",
        2: "WEAK",
        3: "GOOD_NOT_ENOUGH",
        4: "CLEAR_PASS",
        5: "OUTSTANDING"
    }
    return names.get(level, "UNKNOWN")


def has_spec(state: InterviewState) -> bool:
    """Check if state has an interview spec."""
    return state.get("interview_spec") is not None


def get_spec_interview_type(state: InterviewState) -> Optional[str]:
    """Get the interview type from the spec, if present."""
    spec = state.get("interview_spec")
    if spec:
        return spec.get("interview_type")
    return None


def get_current_phase_config(state: InterviewState) -> Optional[Dict[str, Any]]:
    """Get the current phase configuration from the spec."""
    spec = state.get("interview_spec")
    if not spec:
        return None

    current_phase_id = state.get("current_phase", "").lower()
    for phase in spec.get("phases", []):
        if phase.get("id", "").lower() == current_phase_id:
            return phase

    return None


def get_heuristics(state: InterviewState) -> Optional[Dict[str, Any]]:
    """Get the interviewer heuristics from the spec."""
    spec = state.get("interview_spec")
    if spec:
        return spec.get("heuristics")
    return None


def get_context_packet(state: InterviewState) -> Optional[Dict[str, Any]]:
    """Get the context packet from the spec."""
    spec = state.get("interview_spec")
    if spec:
        return spec.get("context_packet")
    return None
