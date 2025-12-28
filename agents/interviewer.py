"""
Interviewer Agent - Candidate-facing conversation handler.
This is the ONLY agent the candidate interacts with.
"""
from typing import Dict, Any
from datetime import datetime
import json

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
        return {
            "spoken": response_text,
            "assessment": {
                "level": 0,
                "trend": "STABLE",
                "thinking": "Could not parse assessment",
                "red_flags_observed": [],
                "green_flags_observed": []
            }
        }


def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the interviewer's response to the candidate.
    """
    # Check if interview is complete
    if state.get("is_complete"):
        return generate_closing_message(state)

    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message(state)

    # Build case data for the dynamic prompt
    case_data = get_case_data(state)

    # Get the system prompt with case context built in
    system_prompt = get_interviewer_system_prompt(case_data)

    # Get recent conversation
    recent_messages = state["messages"][-10:]
    conversation_history = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Current assessment context
    current_level = state.get("current_level", 0)
    level_name = state.get("level_name", "NOT_ASSESSED")
    level_trend = state.get("level_trend", "STABLE")

    context = f"""## Current Session State

**Assessment So Far:**
- Level: {current_level} ({level_name})
- Trend: {level_trend}
- Red flags observed: {state.get("red_flags_observed", [])}
- Green flags observed: {state.get("green_flags_observed", [])}

**Conversation:**
{conversation_history}

---

Respond to the candidate's last message."""

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

    # Extract assessment
    assessment = parsed.get("assessment", {})
    new_level = assessment.get("level", state.get("current_level", 0))
    new_trend = assessment.get("trend", "STABLE")

    # Map level number to name
    level_names = {
        1: "FAIL",
        2: "WEAK",
        3: "GOOD_NOT_ENOUGH",
        4: "CLEAR_PASS",
        5: "OUTSTANDING"
    }
    new_level_name = level_names.get(new_level, "NOT_ASSESSED")

    # Accumulate red flags and green flags (don't duplicate)
    current_red_flags = list(state.get("red_flags_observed", []))
    current_green_flags = list(state.get("green_flags_observed", []))

    for flag in assessment.get("red_flags_observed", []):
        if flag and flag not in current_red_flags:
            current_red_flags.append(flag)

    for flag in assessment.get("green_flags_observed", []):
        if flag and flag not in current_green_flags:
            current_green_flags.append(flag)

    # Track level history
    level_history = list(state.get("level_history", []))
    if new_level > 0:
        level_history.append({
            "level": new_level,
            "trend": new_trend,
            "thinking": assessment.get("thinking", ""),
            "timestamp": datetime.utcnow().isoformat()
        })

    return {
        "messages": state["messages"] + [new_message],
        "current_level": new_level,
        "level_name": new_level_name,
        "level_trend": new_trend,
        "level_history": level_history,
        "red_flags_observed": current_red_flags,
        "green_flags_observed": current_green_flags,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }


def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation using the opening from case data."""
    # The opening now comes directly from the case file
    opening = state["opening"]

    new_message = Message(
        role="interviewer",
        content=opening,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": [new_message],
        "current_phase": "STRUCTURING",
    }


def generate_closing_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the interview closing."""
    current_level = state.get("current_level", 0)

    closing = """That's a good place to wrap up. Thank you for working through this case with me."""

    new_message = Message(
        role="interviewer",
        content=closing,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": state["messages"] + [new_message],
        "is_complete": True,
        "final_score": current_level,
        "current_phase": "COMPLETE",
    }
