"""
Interview Specification System

This module provides the Context Injection architecture for the interview system.
The core principle: ONE interviewer agent that adapts based on what context it receives.

Usage:
    from specs import (
        InterviewSpec,
        InterviewType,
        create_case_interview_spec,
        create_first_round_spec,
        create_technical_interview_spec,
        generate_first_round_spec,  # LLM-powered generator
        UNIVERSAL_RUBRIC,
    )

    # Create a case interview spec from case data
    spec = create_case_interview_spec(case_data)

    # Generate a first-round spec with LLM parsing of JD/CV
    spec = generate_first_round_spec(
        job_description="...",
        candidate_cv="...",
        role_title="Senior PM"
    )

    # Or load an existing spec
    spec = load_spec_from_json("path/to/spec.json")
"""

from .spec_schema import (
    # Enums
    InterviewType,
    ContextPacketType,
    ConfidenceLevel,
    Urgency,
    CompetencyTier,

    # Context Packets
    ContextPacket,
    CVScreenContext,
    CaseStudyContext,
    TechnicalProblemContext,

    # Competency System
    UniversalCompetency,
    RubricLevel,
    SelectedCompetency,
    CompetencyScore,
    UNIVERSAL_RUBRIC,
    get_competency,
    get_competencies_for_type,

    # Heuristics & Phases
    InterviewerHeuristics,
    PhaseConfig,
    SessionConstraints,

    # Manager Output
    ManagerDirective,

    # Main Spec
    InterviewSpec,
    validate_spec,
)

from .spec_loader import (
    load_template,
    load_spec_from_json,
    save_spec_to_json,
    create_case_interview_spec,
    create_first_round_spec,
    create_technical_interview_spec,
    get_available_templates,
    get_competencies_summary,
)

from .generators import (
    generate_first_round_spec,
    generate_first_round_spec_simple,
    generate_specs_for_candidates,
)

__all__ = [
    # Enums
    "InterviewType",
    "ContextPacketType",
    "ConfidenceLevel",
    "Urgency",
    "CompetencyTier",

    # Context Packets
    "ContextPacket",
    "CVScreenContext",
    "CaseStudyContext",
    "TechnicalProblemContext",

    # Competency System
    "UniversalCompetency",
    "RubricLevel",
    "SelectedCompetency",
    "CompetencyScore",
    "UNIVERSAL_RUBRIC",
    "get_competency",
    "get_competencies_for_type",

    # Heuristics & Phases
    "InterviewerHeuristics",
    "PhaseConfig",
    "SessionConstraints",

    # Manager Output
    "ManagerDirective",

    # Main Spec
    "InterviewSpec",
    "validate_spec",

    # Loader Functions
    "load_template",
    "load_spec_from_json",
    "save_spec_to_json",
    "create_case_interview_spec",
    "create_first_round_spec",
    "create_technical_interview_spec",
    "get_available_templates",
    "get_competencies_summary",

    # Generators (LLM-powered)
    "generate_first_round_spec",
    "generate_first_round_spec_simple",
    "generate_specs_for_candidates",
]
