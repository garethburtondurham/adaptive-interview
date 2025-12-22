"""
LangGraph construction for the Adaptive Case Interview System.
"""
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import InterviewState, Message
from agents.evaluator import evaluator_node
from agents.interviewer import interviewer_node
from agents.director import director_node, should_continue


def create_interview_graph():
    """
    Create the LangGraph for the interview system.

    Flow:
    1. Interviewer responds to candidate
    2. Check if candidate is struggling
    3. If struggling → Evaluator provides hint → back to Interviewer
    4. If not struggling → Director checks if interview should continue
    5. Loop back or End
    """
    # Create the graph with InterviewState
    graph = StateGraph(InterviewState)

    # Add nodes
    graph.add_node("interviewer", interviewer_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("director", director_node)

    # Set entry point
    graph.set_entry_point("interviewer")

    # Define edges
    # After evaluator, go to director
    graph.add_edge("evaluator", "director")

    # Director decides whether to continue
    graph.add_conditional_edges(
        "director",
        should_continue,
        {
            "continue": "interviewer",
            "end": END,
        },
    )

    # Compile with memory for state persistence
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


class InterviewRunner:
    """
    High-level interface for running interviews.
    Handles the turn-by-turn flow without requiring LangGraph knowledge.

    New flow:
    - Interviewer responds to each candidate message
    - If interviewer detects struggling → call evaluator for hint
    - If not struggling → continue conversation directly
    """

    def __init__(self, initial_state: InterviewState):
        self.state = initial_state

    def start(self) -> str:
        """
        Start the interview and return the opening message.
        """
        # Generate opening message
        result = interviewer_node(self.state)
        self.state = {**self.state, **result}
        return self._get_last_interviewer_message()

    def respond(self, candidate_response: str) -> str:
        """
        Process candidate's response and return interviewer's next message.

        Flow:
        1. Add candidate message to state
        2. Run interviewer (which detects if candidate is struggling)
        3. If struggling, run evaluator to get a hint, then run interviewer again
        4. Run director to check if we should continue
        """
        # Add candidate message to state
        candidate_message = Message(
            role="candidate",
            content=candidate_response,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.state["messages"] = self.state["messages"] + [candidate_message]

        # Run interviewer - this will detect if candidate is struggling
        interviewer_result = interviewer_node(self.state)
        self.state = {**self.state, **interviewer_result}

        # Check if candidate was struggling and we should get help from evaluator
        if self.state.get("candidate_struggling", False):
            # Run evaluator to get a hint
            evaluator_result = evaluator_node(self.state)
            self.state = {**self.state, **evaluator_result}

            # If evaluator provided a hint, run interviewer again to incorporate it
            if self.state.get("pending_hint"):
                # Remove the last interviewer message (we'll regenerate with hint)
                messages = self.state["messages"]
                if messages and messages[-1]["role"] == "interviewer":
                    self.state["messages"] = messages[:-1]

                # Run interviewer again with the hint
                interviewer_result = interviewer_node(self.state)
                self.state = {**self.state, **interviewer_result}

        # Run director to check constraints
        director_result = director_node(self.state)
        self.state = {**self.state, **director_result}

        # Check if interview should end
        if self.state.get("is_complete"):
            # Generate closing message if not already done
            if not self._last_message_is_closing():
                from agents.interviewer import generate_closing_message
                closing_result = generate_closing_message(self.state)
                self.state = {**self.state, **closing_result}

        return self._get_last_interviewer_message()

    def _get_last_interviewer_message(self) -> str:
        """Get the most recent interviewer message."""
        for msg in reversed(self.state["messages"]):
            if msg["role"] == "interviewer":
                return msg["content"]
        return ""

    def _last_message_is_closing(self) -> bool:
        """Check if the last message is already a closing message."""
        if not self.state["messages"]:
            return False
        last = self.state["messages"][-1]
        return last["role"] == "interviewer" and "wrap up" in last["content"].lower()

    def is_complete(self) -> bool:
        """Check if the interview is complete."""
        return self.state.get("is_complete", False)

    def get_state(self) -> InterviewState:
        """Get the current interview state."""
        return self.state

    def get_scores(self) -> List[Dict[str, Any]]:
        """Get all question scores."""
        return self.state.get("question_scores", [])

    def get_final_score(self) -> float:
        """Get the final average score."""
        return self.state.get("final_score")

    def get_messages(self) -> List[Message]:
        """Get all conversation messages."""
        return self.state.get("messages", [])

    def get_areas_explored(self) -> List[str]:
        """Get list of exploration areas that have been covered."""
        return self.state.get("areas_explored", [])

    def get_key_elements(self) -> List[str]:
        """Get list of key elements the candidate has demonstrated."""
        return self.state.get("key_elements_detected", [])


def create_interview_runner():
    """Factory function to create InterviewRunner class."""
    return InterviewRunner
