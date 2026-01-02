"""
Interview Spec Generators

This module contains generators that create InterviewSpecs from various inputs.

Generators:
- first_round_generator: Creates specs from JD + CV using LLM parsing

Usage:
    from specs.generators import generate_first_round_spec

    spec = generate_first_round_spec(
        job_description="...",
        candidate_cv="...",
        role_title="Senior Product Manager"
    )
"""

from .first_round_generator import (
    generate_first_round_spec,
    generate_first_round_spec_simple,
    generate_specs_for_candidates,
)

__all__ = [
    "generate_first_round_spec",
    "generate_first_round_spec_simple",
    "generate_specs_for_candidates",
]
