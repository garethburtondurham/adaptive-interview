"""
Spec Loader

Utilities for loading InterviewSpecs from JSON files and templates.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from .spec_schema import (
    InterviewSpec,
    InterviewType,
    ContextPacket,
    ContextPacketType,
    CaseStudyContext,
    CVScreenContext,
    TechnicalProblemContext,
    SelectedCompetency,
    CompetencyTier,
    InterviewerHeuristics,
    PhaseConfig,
    SessionConstraints,
    validate_spec,
    UNIVERSAL_RUBRIC,
)

# Paths
SPECS_DIR = Path(__file__).parent
TEMPLATES_DIR = SPECS_DIR / "templates"


def load_template(template_name: str) -> Dict[str, Any]:
    """Load a template JSON file"""
    template_path = TEMPLATES_DIR / f"{template_name}.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_spec_from_json(json_path: str) -> InterviewSpec:
    """Load a complete InterviewSpec from a JSON file"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return InterviewSpec(**data)


def save_spec_to_json(spec: InterviewSpec, json_path: str) -> None:
    """Save an InterviewSpec to a JSON file"""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(spec.model_dump(), f, indent=2)


def create_case_interview_spec(
    case_data: Dict[str, Any],
    spec_id: Optional[str] = None,
    template_name: str = "case_interview_template"
) -> InterviewSpec:
    """
    Create an InterviewSpec for a case interview from case data.

    Args:
        case_data: Dictionary containing case content (prompt, facts, etc.)
        spec_id: Optional ID for the spec (generated if not provided)
        template_name: Template to use for heuristics and phases

    Returns:
        Complete InterviewSpec ready for use
    """
    # Load template for defaults
    template = load_template(template_name)

    # Generate spec ID if not provided
    if not spec_id:
        spec_id = f"case_{case_data.get('id', uuid.uuid4().hex[:8])}"

    # Build context packet
    context_packet = ContextPacket(
        packet_type=ContextPacketType.CASE_STUDY,
        case_study=CaseStudyContext(
            case_prompt=case_data["opening"],
            facts=case_data.get("facts", {}),
            root_cause=case_data.get("root_cause", ""),
            strong_recommendations=case_data.get("strong_recommendations", []),
            calibration_examples=case_data.get("calibration", {})
        )
    )

    # Build competencies from template defaults
    competencies = []
    for comp_config in template.get("competencies", []):
        comp_id = comp_config["id"]

        # Skip if not in universal rubric
        if comp_id not in UNIVERSAL_RUBRIC:
            continue

        competencies.append(SelectedCompetency(
            competency_id=comp_id,
            tier=CompetencyTier(comp_config.get("tier", "important")),
            additional_red_flags=case_data.get("red_flags", []) if comp_config.get("inherit_case_flags") else [],
            additional_green_flags=case_data.get("green_flags", []) if comp_config.get("inherit_case_flags") else [],
        ))

    # Build heuristics from template
    heuristics_data = template.get("heuristics", {})
    heuristics = InterviewerHeuristics(**heuristics_data)

    # Build phases from template
    phases = []
    for phase_data in template.get("phases", []):
        phases.append(PhaseConfig(**phase_data))

    # Build constraints from template
    constraints_data = template.get("constraints", {})
    constraints = SessionConstraints(**constraints_data)

    # Assemble spec
    spec = InterviewSpec(
        spec_id=spec_id,
        interview_type=InterviewType.CASE,
        title=case_data.get("title", "Case Interview"),
        version="1.0",
        context_packet=context_packet,
        competencies=competencies,
        heuristics=heuristics,
        phases=phases,
        constraints=constraints,
        template_id=template_name
    )

    # Validate
    issues = validate_spec(spec)
    if issues:
        raise ValueError(f"Invalid spec: {issues}")

    return spec


def create_first_round_spec(
    job_description: str,
    candidate_cv: str,
    role_title: str,
    company_context: Optional[str] = None,
    spec_id: Optional[str] = None,
    template_name: str = "first_round_template",
    parsed_data: Optional[Dict[str, Any]] = None
) -> InterviewSpec:
    """
    Create an InterviewSpec for a first-round screening interview.

    Args:
        job_description: The job description text
        candidate_cv: The candidate's CV/resume text
        role_title: Title of the role
        company_context: Optional company context
        spec_id: Optional ID for the spec
        template_name: Template to use
        parsed_data: Optional pre-parsed JD/CV data (jd_requirements, cv_claims, etc.)

    Returns:
        Complete InterviewSpec ready for use
    """
    # Load template
    template = load_template(template_name)

    # Generate spec ID
    if not spec_id:
        spec_id = f"first_round_{uuid.uuid4().hex[:8]}"

    # Build context packet
    context_packet = ContextPacket(
        packet_type=ContextPacketType.CV_SCREEN,
        cv_screen=CVScreenContext(
            job_description=job_description,
            candidate_cv=candidate_cv,
            role_title=role_title,
            company_context=company_context,
            jd_requirements=parsed_data.get("jd_requirements", []) if parsed_data else [],
            cv_claims=parsed_data.get("cv_claims", []) if parsed_data else [],
            gaps_to_probe=parsed_data.get("gaps_to_probe", []) if parsed_data else [],
            claims_to_validate=parsed_data.get("claims_to_validate", []) if parsed_data else []
        )
    )

    # Build competencies from template
    competencies = []
    for comp_config in template.get("competencies", []):
        comp_id = comp_config["id"]
        if comp_id not in UNIVERSAL_RUBRIC:
            continue

        competencies.append(SelectedCompetency(
            competency_id=comp_id,
            tier=CompetencyTier(comp_config.get("tier", "important")),
        ))

    # Build heuristics from template
    heuristics = InterviewerHeuristics(**template.get("heuristics", {}))

    # Build phases from template
    phases = [PhaseConfig(**p) for p in template.get("phases", [])]

    # Build constraints from template
    constraints = SessionConstraints(**template.get("constraints", {}))

    # Assemble spec
    spec = InterviewSpec(
        spec_id=spec_id,
        interview_type=InterviewType.FIRST_ROUND,
        title=f"First Round - {role_title}",
        version="1.0",
        context_packet=context_packet,
        competencies=competencies,
        heuristics=heuristics,
        phases=phases,
        constraints=constraints,
        template_id=template_name
    )

    # Validate
    issues = validate_spec(spec)
    if issues:
        raise ValueError(f"Invalid spec: {issues}")

    return spec


def create_technical_interview_spec(
    problem_data: Dict[str, Any],
    spec_id: Optional[str] = None,
    template_name: str = "technical_interview_template"
) -> InterviewSpec:
    """
    Create an InterviewSpec for a technical interview.

    Args:
        problem_data: Dictionary containing problem content
        spec_id: Optional ID for the spec
        template_name: Template to use

    Returns:
        Complete InterviewSpec ready for use
    """
    # Load template
    template = load_template(template_name)

    # Generate spec ID
    if not spec_id:
        spec_id = f"technical_{problem_data.get('id', uuid.uuid4().hex[:8])}"

    # Build context packet
    context_packet = ContextPacket(
        packet_type=ContextPacketType.TECHNICAL_PROBLEM,
        technical_problem=TechnicalProblemContext(
            problem_statement=problem_data["problem_statement"],
            starter_code=problem_data.get("starter_code"),
            test_cases=problem_data.get("test_cases", []),
            expected_complexity=problem_data.get("expected_complexity"),
            available_hints=problem_data.get("hints", []),
            solution_approach=problem_data.get("solution_approach", ""),
            common_pitfalls=problem_data.get("common_pitfalls", []),
            edge_cases=problem_data.get("edge_cases", [])
        )
    )

    # Build competencies from template
    competencies = []
    for comp_config in template.get("competencies", []):
        comp_id = comp_config["id"]
        if comp_id not in UNIVERSAL_RUBRIC:
            continue

        competencies.append(SelectedCompetency(
            competency_id=comp_id,
            tier=CompetencyTier(comp_config.get("tier", "important")),
        ))

    # Build heuristics from template
    heuristics = InterviewerHeuristics(**template.get("heuristics", {}))

    # Build phases from template
    phases = [PhaseConfig(**p) for p in template.get("phases", [])]

    # Build constraints from template
    constraints = SessionConstraints(**template.get("constraints", {}))

    # Assemble spec
    spec = InterviewSpec(
        spec_id=spec_id,
        interview_type=InterviewType.TECHNICAL,
        title=problem_data.get("title", "Technical Interview"),
        version="1.0",
        context_packet=context_packet,
        competencies=competencies,
        heuristics=heuristics,
        phases=phases,
        constraints=constraints,
        template_id=template_name
    )

    # Validate
    issues = validate_spec(spec)
    if issues:
        raise ValueError(f"Invalid spec: {issues}")

    return spec


def get_available_templates() -> List[str]:
    """List all available template names"""
    if not TEMPLATES_DIR.exists():
        return []

    return [
        f.stem for f in TEMPLATES_DIR.glob("*.json")
    ]


def get_competencies_summary(spec: InterviewSpec) -> Dict[str, Any]:
    """
    Get a summary of competencies for display.
    Groups by tier and includes full rubric info.
    """
    summary = {
        "critical": [],
        "important": [],
        "bonus": []
    }

    for selected in spec.competencies:
        full_comp = selected.get_full_competency()
        tier_key = selected.tier.value if isinstance(selected.tier, CompetencyTier) else selected.tier

        summary[tier_key].append({
            "id": selected.competency_id,
            "name": full_comp.name,
            "description": full_comp.description,
            "red_flags": full_comp.red_flags,
            "green_flags": full_comp.green_flags
        })

    return summary
