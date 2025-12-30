"""
State definitions for the Adaptive Case Interview System.
"""
from typing import TypedDict, List, Optional, Literal
from enum import Enum


class Phase(str, Enum):
    INTRO = "INTRO"
    STRUCTURING = "STRUCTURING"
    ANALYSIS = "ANALYSIS"
    CALCULATION = "CALCULATION"
    SYNTHESIS = "SYNTHESIS"
    COMPLETE = "COMPLETE"


class Message(TypedDict):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    timestamp: str


class QuestionScore(TypedDict):
    question_id: str
    phase: str
    score: int  # 1-5
    reasoning: str
    key_elements_detected: List[str]
    difficulty_at_time: int


class InterviewState(TypedDict):
    # Session metadata
    session_id: str
    candidate_id: Optional[str]
    case_id: str
    started_at: str

    # Case content (loaded from JSON) - new structure
    case_title: str
    opening: str  # The case prompt presented to candidate
    facts: dict  # All case facts (provided when earned)
    root_cause: str  # The actual answer
    strong_recommendations: List[str]  # What good recommendations look like
    calibration: dict  # Level examples for calibration
    case_red_flags: List[str]  # Red flags defined in case
    case_green_flags: List[str]  # Green flags defined in case

    # Current position
    current_phase: str

    # Conversation tracking
    messages: List[Message]

    # Performance tracking
    current_level: int  # 1-5 assessment level
    level_name: str  # FAIL, WEAK, GOOD_NOT_ENOUGH, CLEAR_PASS, OUTSTANDING
    level_trend: str  # UP, STABLE, DOWN
    level_history: List[dict]  # Track level changes over time
    red_flags_observed: List[str]  # Red flags actually observed in this interview
    green_flags_observed: List[str]  # Green flags actually observed in this interview

    # Evaluator guidance (set by evaluator, used by interviewer)
    evaluator_action: str  # DO_NOT_HELP, MINIMAL_HELP, LIGHT_HELP, CHALLENGE, LET_SHINE
    evaluator_guidance: str  # Specific guidance for interviewer
    data_to_share: Optional[str]  # Data evaluator has approved for sharing

    # Scoring (only populated when evaluator is called)
    question_scores: List[QuestionScore]

    # Control
    is_complete: bool
    final_score: Optional[float]
    final_summary: Optional[str]

    # Usage tracking
    total_tokens: int
