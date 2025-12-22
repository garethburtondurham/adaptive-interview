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


class Directive(str, Enum):
    PROVIDE_HINT = "PROVIDE_HINT"
    PROCEED_STANDARD = "PROCEED_STANDARD"
    ADD_COMPLEXITY = "ADD_COMPLEXITY"
    REPEAT_SIMPLIFIED = "REPEAT_SIMPLIFIED"
    MOVE_TO_NEXT_PHASE = "MOVE_TO_NEXT_PHASE"
    END_INTERVIEW = "END_INTERVIEW"


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


class EvaluatorOutput(TypedDict):
    score: int
    reasoning: str
    key_elements_detected: List[str]
    directive: str
    hint_if_needed: Optional[str]
    complexity_addition: Optional[str]
    data_to_reveal: Optional[str]


class InterviewState(TypedDict):
    # Session metadata
    session_id: str
    candidate_id: Optional[str]
    case_id: str
    started_at: str

    # Case content (loaded from JSON)
    case_title: str
    case_prompt: str
    hidden_facts: dict
    question_sequence: List[dict]

    # Current position
    current_phase: str
    current_question_index: int
    difficulty_level: int  # 1-5

    # Conversation
    messages: List[Message]

    # Scoring
    question_scores: List[QuestionScore]

    # Agent communication
    last_evaluator_output: Optional[EvaluatorOutput]
    next_directive: Optional[str]
    pending_hint: Optional[str]
    pending_complexity: Optional[str]
    pending_data_reveal: Optional[str]

    # Control
    is_complete: bool
    final_score: Optional[float]
    final_summary: Optional[str]
