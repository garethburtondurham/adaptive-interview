"""
Prompt templates for agents.
"""
from .evaluator_prompt import get_evaluator_system_prompt
from .interviewer_prompt import get_interviewer_system_prompt

__all__ = ["get_evaluator_system_prompt", "get_interviewer_system_prompt"]
