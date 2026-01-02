"""
First Round Interview Spec Generator

This module generates InterviewSpecs for first-round screening interviews
by parsing job descriptions and candidate CVs using an LLM.

The generator:
1. Parses the JD for required skills, experience, and competencies
2. Parses the CV for claimed experience and accomplishments
3. Identifies gaps (JD requirements not evidenced in CV)
4. Identifies probing targets (specific claims to validate)
5. Assembles a complete InterviewSpec customized to this candidate
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from specs.spec_schema import (
    InterviewSpec,
    InterviewType,
    ContextPacket,
    ContextPacketType,
    CVScreenContext,
    SelectedCompetency,
    CompetencyTier,
    InterviewerHeuristics,
    PhaseConfig,
    SessionConstraints,
    validate_spec,
)
from specs.spec_loader import load_template

# Initialize LLM for parsing
parser_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.2,
    max_tokens=2048,
)


def generate_first_round_spec(
    job_description: str,
    candidate_cv: str,
    role_title: str,
    company_context: Optional[str] = None,
    template_name: str = "first_round_template"
) -> InterviewSpec:
    """
    Generate a complete InterviewSpec for a first-round screening interview.

    This function uses an LLM to:
    1. Parse the JD for requirements
    2. Parse the CV for claims
    3. Identify gaps and probing targets
    4. Customize the interview spec for this specific candidate

    Args:
        job_description: The full job description text
        candidate_cv: The candidate's CV/resume text
        role_title: Title of the role (e.g., "Senior Product Manager")
        company_context: Optional context about the company
        template_name: Template to use for base heuristics and phases

    Returns:
        Complete InterviewSpec ready for use
    """
    # Load the base template
    template = load_template(template_name)

    # Parse JD and CV using LLM
    parsed_data = _parse_jd_and_cv(job_description, candidate_cv, role_title)

    # Generate spec ID
    spec_id = f"first_round_{uuid.uuid4().hex[:8]}"

    # Build context packet with parsed data
    context_packet = ContextPacket(
        packet_type=ContextPacketType.CV_SCREEN,
        cv_screen=CVScreenContext(
            job_description=job_description,
            candidate_cv=candidate_cv,
            role_title=role_title,
            company_context=company_context,
            jd_requirements=parsed_data.get("jd_requirements", []),
            cv_claims=parsed_data.get("cv_claims", []),
            gaps_to_probe=parsed_data.get("gaps_to_probe", []),
            claims_to_validate=parsed_data.get("claims_to_validate", [])
        )
    )

    # Build competencies - use template defaults, potentially customize based on JD
    competencies = _build_competencies(template, parsed_data)

    # Build heuristics from template
    heuristics = InterviewerHeuristics(**template.get("heuristics", {}))

    # Build phases - potentially customize based on gaps
    phases = _build_phases(template, parsed_data)

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
        # Log issues but don't fail - the spec should still work
        print(f"Spec validation warnings: {issues}")

    return spec


def _parse_jd_and_cv(
    job_description: str,
    candidate_cv: str,
    role_title: str
) -> Dict[str, Any]:
    """
    Use LLM to parse job description and CV, identifying gaps and probing targets.
    """

    system_prompt = """You are an expert recruiter analyzing a job description and candidate CV.

Your task is to:
1. Extract key requirements from the job description
2. Extract key claims/experience from the CV
3. Identify GAPS: Requirements in the JD that are NOT clearly evidenced in the CV
4. Identify PROBING TARGETS: Specific claims in the CV that should be validated with depth questions

Be specific and actionable. Focus on the most important items (max 5-7 per category).

Respond with valid JSON only."""

    user_prompt = f"""## Role
{role_title}

## Job Description
{job_description}

## Candidate CV
{candidate_cv}

---

Analyze and respond with this JSON structure:

```json
{{
    "jd_requirements": [
        "Requirement 1 (e.g., '5+ years product management experience')",
        "Requirement 2",
        ...
    ],
    "cv_claims": [
        "Claim 1 (e.g., 'Led team of 10 engineers at Company X')",
        "Claim 2",
        ...
    ],
    "gaps_to_probe": [
        "Gap 1: JD requirement not evidenced in CV (e.g., 'JD requires SQL skills - not mentioned in CV')",
        "Gap 2",
        ...
    ],
    "claims_to_validate": [
        "Claim to validate with specific questions (e.g., 'Claims 40% revenue increase - probe for specifics, methodology, their role')",
        "Claim 2",
        ...
    ],
    "seniority_match": "strong|moderate|weak",
    "overall_fit_hypothesis": "Brief assessment of likely fit based on paper review"
}}
```"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = parser_llm.invoke(messages)
        return _parse_json_response(response.content)
    except Exception as e:
        print(f"Error parsing JD/CV: {e}")
        # Return empty parsed data - interview can still proceed
        return {
            "jd_requirements": [],
            "cv_claims": [],
            "gaps_to_probe": [],
            "claims_to_validate": [],
            "seniority_match": "unknown",
            "overall_fit_hypothesis": "Unable to parse - proceed with standard first round"
        }


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def _build_competencies(
    template: Dict[str, Any],
    parsed_data: Dict[str, Any]
) -> List[SelectedCompetency]:
    """Build competency list, potentially customizing based on parsed JD."""

    competencies = []

    # Start with template competencies
    for comp_config in template.get("competencies", []):
        comp_id = comp_config.get("id")
        tier = CompetencyTier(comp_config.get("tier", "important"))

        competencies.append(SelectedCompetency(
            competency_id=comp_id,
            tier=tier,
        ))

    # If we detected weak seniority match, elevate experience_depth to critical
    seniority_match = parsed_data.get("seniority_match", "moderate")
    if seniority_match == "weak":
        for comp in competencies:
            if comp.competency_id == "experience_depth":
                comp.tier = CompetencyTier.CRITICAL

    return competencies


def _build_phases(
    template: Dict[str, Any],
    parsed_data: Dict[str, Any]
) -> List[PhaseConfig]:
    """Build phase list, potentially customizing based on gaps."""

    phases = []

    for phase_data in template.get("phases", []):
        phase = PhaseConfig(**phase_data)

        # If we have significant gaps, extend the gap_exploration phase
        gaps = parsed_data.get("gaps_to_probe", [])
        if phase.id == "gap_exploration" and len(gaps) >= 3:
            phase.suggested_max_exchanges = 5  # More time for gaps
            phase.objective = f"Probe {len(gaps)} identified gaps in experience"

        phases.append(phase)

    return phases


def generate_first_round_spec_simple(
    job_description: str,
    candidate_cv: str,
    role_title: str,
    company_context: Optional[str] = None
) -> InterviewSpec:
    """
    Simplified generator that doesn't use LLM parsing.

    Use this for quick setup or when LLM parsing is not needed.
    The interviewer will still adapt based on the JD and CV content.
    """
    from specs.spec_loader import create_first_round_spec

    return create_first_round_spec(
        job_description=job_description,
        candidate_cv=candidate_cv,
        role_title=role_title,
        company_context=company_context
    )


# =============================================================================
# BATCH GENERATION
# =============================================================================

def generate_specs_for_candidates(
    job_description: str,
    role_title: str,
    candidates: List[Dict[str, Any]],
    company_context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate specs for multiple candidates for the same role.

    Args:
        job_description: The job description
        role_title: The role title
        candidates: List of dicts with 'id' and 'cv' keys
        company_context: Optional company context

    Returns:
        List of dicts with 'candidate_id', 'spec', and 'parsed_data'
    """
    results = []

    for candidate in candidates:
        try:
            spec = generate_first_round_spec(
                job_description=job_description,
                candidate_cv=candidate.get("cv", ""),
                role_title=role_title,
                company_context=company_context
            )

            results.append({
                "candidate_id": candidate.get("id"),
                "spec": spec,
                "success": True
            })
        except Exception as e:
            results.append({
                "candidate_id": candidate.get("id"),
                "error": str(e),
                "success": False
            })

    return results
