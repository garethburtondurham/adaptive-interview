"""
Interviewer Agent - Candidate-facing conversation handler.
This is the ONLY agent the candidate interacts with.
"""
from typing import Dict, Any
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import InterviewState, Message, Directive
from case_loader import get_current_question
from prompts.interviewer_prompt import get_interviewer_system_prompt

# Initialize LLM (slightly higher temperature for natural conversation)
interviewer_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=512,
)


def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the interviewer's response to the candidate.
    This is the ONLY agent the candidate interacts with.
    """
    current_question = get_current_question(state)
    directive = state.get("next_directive", Directive.PROCEED_STANDARD.value)

    # Check if interview is complete
    if state.get("is_complete") or current_question is None:
        return generate_closing_message(state)

    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message(state)

    # Build context for the interviewer
    system_prompt = get_interviewer_system_prompt()

    # Get recent conversation for context (last 6 messages)
    recent_messages = state["messages"][-6:]
    conversation_history = "\n".join(
        [
            f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
            for m in recent_messages
        ]
    )

    context = f"""
## Case Title
{state["case_title"]}

## Current Phase
{state["current_phase"]}

## Recent Conversation
{conversation_history}

## Directive from Evaluator
{directive}

## Current Question to Ask (if moving forward)
{current_question.get("prompt", "")}

## Hint to Provide (if directive is PROVIDE_HINT)
{state.get("pending_hint", "None")}

## Complexity to Add (if directive is ADD_COMPLEXITY)
{state.get("pending_complexity", "None")}

## Data to Reveal (if candidate asked for information)
{state.get("pending_data_reveal", "None")}

## Hidden Facts (DO NOT reveal unless candidate specifically asks)
Available data categories: {list(state["hidden_facts"].keys())}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    response = interviewer_llm.invoke(messages)

    new_message = Message(
        role="interviewer",
        content=response.content,
        timestamp=datetime.utcnow().isoformat(),
    )

    # Clear the pending directives after using them
    return {
        "messages": state["messages"] + [new_message],
        "pending_hint": None,
        "pending_complexity": None,
        "pending_data_reveal": None,
    }


def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation."""
    opening = f"""Welcome! I'm excited to work through a case with you today.

Let me set the scene: {state["case_prompt"]}

Before we dive in, take a moment to think about how you'd approach this. What would be your initial framework for analyzing this problem?"""

    new_message = Message(
        role="interviewer",
        content=opening,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {"messages": [new_message], "current_phase": "STRUCTURING"}


def generate_closing_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the interview closing."""
    # Calculate final score
    scores = [qs["score"] for qs in state["question_scores"]]
    avg_score = sum(scores) / len(scores) if scores else 0

    closing = """Excellent, that's a good place to wrap up. You've worked through the key elements of this case well.

Thank you for your time today. We'll be in touch with next steps soon."""

    new_message = Message(
        role="interviewer",
        content=closing,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": state["messages"] + [new_message],
        "is_complete": True,
        "final_score": round(avg_score, 2),
        "current_phase": "COMPLETE",
    }
