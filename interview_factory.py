"""
Interview Factory

Convenience functions for creating interviews of different types.
This is the recommended entry point for creating new interviews.

Usage:
    from interview_factory import (
        create_case_interview,
        create_first_round_interview,
        create_technical_interview,
    )

    # Case interview from case data
    runner = create_case_interview(case_data, candidate_id="candidate_123")
    opening = runner.start()

    # First round interview from JD/CV
    runner = create_first_round_interview(
        job_description="...",
        candidate_cv="...",
        role_title="Senior PM"
    )

    # Technical interview from problem data
    runner = create_technical_interview(problem_data)
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from graph import InterviewRunner, initialize_from_spec
from specs import (
    create_case_interview_spec,
    create_first_round_spec,
    create_technical_interview_spec,
    generate_first_round_spec,
    generate_first_round_spec_simple,
    InterviewSpec,
)


# =============================================================================
# CASE INTERVIEW
# =============================================================================

def create_case_interview(
    case_data: Dict[str, Any],
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create a case interview from case data.

    This creates a complete interview ready to run, using the case interview
    template for heuristics and phases.

    Args:
        case_data: Dictionary containing case content:
            - opening: The case prompt
            - facts: Dictionary of case facts
            - root_cause: The actual answer
            - strong_recommendations: Example good answers
            - calibration: Level examples (optional)
            - title: Case title (optional)
            - id: Case ID (optional)

        candidate_id: Optional identifier for the candidate
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start

    Example:
        case_data = {
            "opening": "Your client is a coffee shop chain...",
            "facts": {"revenue": "$10M", "stores": 50},
            "root_cause": "Declining foot traffic",
            "strong_recommendations": ["Focus on digital ordering"]
        }
        runner = create_case_interview(case_data)
        opening = runner.start()
    """
    # Create the spec from case data
    spec = create_case_interview_spec(case_data)

    # Create and return the runner
    return InterviewRunner.from_spec(spec, candidate_id, session_id)


def create_case_interview_from_file(
    case_file_path: str,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create a case interview from a JSON case file.

    Args:
        case_file_path: Path to the case JSON file
        candidate_id: Optional candidate identifier
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start
    """
    with open(case_file_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    return create_case_interview(case_data, candidate_id, session_id)


def list_available_cases(cases_dir: str = "cases") -> List[Dict[str, str]]:
    """
    List all available case files.

    Args:
        cases_dir: Directory containing case JSON files

    Returns:
        List of dicts with 'id', 'title', 'path' for each case
    """
    cases_path = Path(cases_dir)
    if not cases_path.exists():
        return []

    cases = []
    for case_file in cases_path.glob("*.json"):
        try:
            with open(case_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                cases.append({
                    "id": data.get("id", case_file.stem),
                    "title": data.get("title", case_file.stem),
                    "path": str(case_file)
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return cases


# =============================================================================
# FIRST ROUND INTERVIEW
# =============================================================================

def create_first_round_interview(
    job_description: str,
    candidate_cv: str,
    role_title: str,
    company_context: Optional[str] = None,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
    use_llm_parsing: bool = True,
) -> InterviewRunner:
    """
    Create a first-round screening interview.

    This creates an interview customized for the specific candidate based on
    their CV and the job description. When LLM parsing is enabled, it will
    identify gaps and probing targets automatically.

    Args:
        job_description: The full job description text
        candidate_cv: The candidate's CV/resume text
        role_title: Title of the role (e.g., "Senior Product Manager")
        company_context: Optional context about the company
        candidate_id: Optional candidate identifier
        session_id: Optional session identifier
        use_llm_parsing: If True, uses LLM to analyze JD/CV and identify
                         gaps and probing targets. Set to False for faster
                         setup without parsing.

    Returns:
        InterviewRunner ready to start

    Example:
        runner = create_first_round_interview(
            job_description="We're looking for a Senior PM with 5+ years...",
            candidate_cv="Experienced PM with 7 years at tech startups...",
            role_title="Senior Product Manager"
        )
        opening = runner.start()
    """
    if use_llm_parsing:
        # Use LLM to parse and identify gaps/probing targets
        spec = generate_first_round_spec(
            job_description=job_description,
            candidate_cv=candidate_cv,
            role_title=role_title,
            company_context=company_context,
        )
    else:
        # Simple spec without LLM parsing
        spec = create_first_round_spec(
            job_description=job_description,
            candidate_cv=candidate_cv,
            role_title=role_title,
            company_context=company_context,
        )

    return InterviewRunner.from_spec(spec, candidate_id, session_id)


def create_first_round_interview_simple(
    job_description: str,
    candidate_cv: str,
    role_title: str,
    company_context: Optional[str] = None,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create a first-round interview without LLM parsing.

    This is faster but doesn't pre-analyze the JD/CV for gaps.
    Use this when you want quick setup or are testing.
    """
    return create_first_round_interview(
        job_description=job_description,
        candidate_cv=candidate_cv,
        role_title=role_title,
        company_context=company_context,
        candidate_id=candidate_id,
        session_id=session_id,
        use_llm_parsing=False,
    )


# =============================================================================
# TECHNICAL INTERVIEW
# =============================================================================

def create_technical_interview(
    problem_data: Dict[str, Any],
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create a technical coding interview.

    Args:
        problem_data: Dictionary containing problem content:
            - problem_statement: The coding problem description
            - starter_code: Optional starter code
            - test_cases: List of test case dicts
            - expected_complexity: e.g., "O(n log n)"
            - hints: List of available hints
            - solution_approach: Expected approach
            - common_pitfalls: Common mistakes to watch for
            - edge_cases: Edge cases to consider
            - title: Problem title (optional)
            - id: Problem ID (optional)

        candidate_id: Optional candidate identifier
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start

    Example:
        problem_data = {
            "problem_statement": "Given an array of integers...",
            "expected_complexity": "O(n)",
            "test_cases": [
                {"input": "[1,2,3]", "expected": "6"}
            ],
            "hints": [
                "Consider using a hash map",
                "Think about edge cases with empty arrays"
            ]
        }
        runner = create_technical_interview(problem_data)
        opening = runner.start()
    """
    spec = create_technical_interview_spec(problem_data)
    return InterviewRunner.from_spec(spec, candidate_id, session_id)


def create_technical_interview_from_file(
    problem_file_path: str,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create a technical interview from a JSON problem file.

    Args:
        problem_file_path: Path to the problem JSON file
        candidate_id: Optional candidate identifier
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start
    """
    with open(problem_file_path, "r", encoding="utf-8") as f:
        problem_data = json.load(f)

    return create_technical_interview(problem_data, candidate_id, session_id)


# =============================================================================
# GENERIC / CUSTOM
# =============================================================================

def create_interview_from_spec(
    spec: InterviewSpec,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create an interview from a pre-built InterviewSpec.

    Use this when you have a custom spec or loaded one from a file.

    Args:
        spec: An InterviewSpec instance
        candidate_id: Optional candidate identifier
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start
    """
    return InterviewRunner.from_spec(spec, candidate_id, session_id)


def create_interview_from_spec_file(
    spec_file_path: str,
    candidate_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> InterviewRunner:
    """
    Create an interview from a JSON spec file.

    Args:
        spec_file_path: Path to the spec JSON file
        candidate_id: Optional candidate identifier
        session_id: Optional session identifier

    Returns:
        InterviewRunner ready to start
    """
    from specs import load_spec_from_json

    spec = load_spec_from_json(spec_file_path)
    return InterviewRunner.from_spec(spec, candidate_id, session_id)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Case interviews
    "create_case_interview",
    "create_case_interview_from_file",
    "list_available_cases",

    # First round interviews
    "create_first_round_interview",
    "create_first_round_interview_simple",

    # Technical interviews
    "create_technical_interview",
    "create_technical_interview_from_file",

    # Generic
    "create_interview_from_spec",
    "create_interview_from_spec_file",
]
