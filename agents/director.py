"""
Director Agent - DEPRECATED, use manager.py instead.

This module is kept for backward compatibility.
All functionality has been moved to manager.py.
"""

# Re-export from manager for backward compatibility
from agents.manager import (
    manager_node as director_node,
    should_continue,
)

__all__ = ["director_node", "should_continue"]
