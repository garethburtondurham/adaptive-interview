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
    1. Interviewer asks question
    2. (External) Candidate responds
    3. Evaluator scores response
    4. Director checks constraints
    5. Loop back to Interviewer or End
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
        """
        # Add candidate message to state
        candidate_message = Message(
            role="candidate",
            content=candidate_response,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.state["messages"] = self.state["messages"] + [candidate_message]

        # Run evaluator
        evaluator_result = evaluator_node(self.state)
        self.state = {**self.state, **evaluator_result}

        # Run director
        director_result = director_node(self.state)
        self.state = {**self.state, **director_result}

        if self.state.get("is_complete"):
            # Generate closing message
            result = interviewer_node(self.state)
            self.state = {**self.state, **result}
        else:
            # Generate next question/response
            result = interviewer_node(self.state)
            self.state = {**self.state, **result}

        return self._get_last_interviewer_message()

    def _get_last_interviewer_message(self) -> str:
        """Get the most recent interviewer message."""
        for msg in reversed(self.state["messages"]):
            if msg["role"] == "interviewer":
                return msg["content"]
        return ""

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


def create_interview_runner():
    """Factory function to create InterviewRunner class."""
    return InterviewRunner
