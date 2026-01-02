"""
Agent modules for the Adaptive Case Interview System.

Agents:
- evaluator: Assessment authority - scores candidate performance
- interviewer: Candidate-facing conversation handler
- manager: Session orchestration and competency coverage (formerly director)
- director: DEPRECATED - alias for manager (backward compatibility)
"""
from .evaluator import evaluator_node
from .interviewer import interviewer_node
from .manager import manager_node, should_continue

# Backward compatibility alias
from .director import director_node

__all__ = [
    "evaluator_node",
    "interviewer_node",
    "manager_node",
    "director_node",  # Deprecated alias
    "should_continue",
]
