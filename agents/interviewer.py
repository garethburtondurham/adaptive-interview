"""
Interviewer Agent - Candidate-facing conversation handler.
Executes the interview methodology and follows evaluator guidance.
This is the ONLY agent the candidate interacts with.
"""
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import json

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import InterviewState, Message
from case_loader import get_case_data
from prompts.interviewer_prompt import get_interviewer_system_prompt

# Initialize LLM
interviewer_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=1024,
)


def parse_interviewer_response(response_text: str) -> Dict[str, Any]:
    """Parse the interviewer's JSON response with fallback handling."""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Fallback: treat the whole response as the spoken message
        return {"spoken": response_text}


def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the interviewer's response to the candidate.
    Follows evaluator guidance for how to respond.
    """
    # Check if interview is complete
    if state.get("is_complete"):
        return generate_closing_message(state)

    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message(state)

    # Build case data for the dynamic prompt
    case_data = get_case_data(state)

    # Get the system prompt with case context
    system_prompt = get_interviewer_system_prompt(case_data)

    # Get recent conversation
    recent_messages = state["messages"][-10:]
    conversation_history = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Get evaluator guidance
    evaluator_action = state.get("evaluator_action", "DO_NOT_HELP")
    evaluator_guidance = state.get("evaluator_guidance", "")
    data_to_share = state.get("data_to_share")

    context = f"""## Evaluator Guidance

**Action:** {evaluator_action}
**Specific guidance:** {evaluator_guidance}
**Data approved to share:** {data_to_share if data_to_share else "None - do not share data unless candidate earns it"}

---

## Conversation So Far

{conversation_history}

---

Respond to the candidate's last message, following the evaluator's guidance and your methodology principles."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    response = interviewer_llm.invoke(messages)
    parsed = parse_interviewer_response(response.content)

    # Track token usage
    usage = response.response_metadata.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    # Extract the spoken message
    spoken = parsed.get("spoken", response.content)

    new_message = Message(
        role="interviewer",
        content=spoken,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": state["messages"] + [new_message],
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }


def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation with introduction expectations."""
    opening = state["opening"]

    # Remove trailing "Over to you." if present (we'll add our own ending)
    opening = opening.replace("\n\nOver to you.", "").replace("Over to you.", "").strip()

    # Brief expectations after the case
    intro = """Take a moment to gather your thoughts. Feel free to ask any clarifying questions, and when you're ready, share how you'd like to approach this. There's no single right answer — I'm interested in your thinking.

Over to you."""

    full_opening = opening + "\n\n" + intro

    new_message = Message(
        role="interviewer",
        content=full_opening,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": [new_message],
        "current_phase": "STRUCTURING",
    }


def generate_closing_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the interview closing."""
    closing = "That's a good place to wrap up. Thank you for working through this case with me."

    new_message = Message(
        role="interviewer",
        content=closing,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": state["messages"] + [new_message],
        "is_complete": True,
        "final_score": state.get("current_level", 0),
        "current_phase": "COMPLETE",
    }
