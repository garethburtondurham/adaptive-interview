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
from case_loader import get_exploration_areas, get_unexplored_areas
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
        return {
            "message": response_text,
            "internal_assessment": {
                "current_level": 0,
                "level_trend": "STABLE",
                "key_observation": "Could not parse assessment"
            },
            "areas_touched": [],
            "current_phase": "ANALYSIS",
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

    # Build context for the interviewer
    system_prompt = get_interviewer_system_prompt()

    # Get recent conversation
    recent_messages = state["messages"][-10:]
    conversation_history = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Get case grading rubric if available
    grading_context = ""
    case_data = state.get("exploration_areas", [])

    # Get all exploration areas
    all_areas = get_exploration_areas(state)
    areas_summary = "\n".join([
        f"- {area['id']}: {area['description']}"
        for area in all_areas
    ])

    # Current assessment context
    current_level = state.get("current_level", 0)
    level_name = state.get("level_name", "NOT_ASSESSED")

    context = f"""
## Case
Title: {state["case_title"]}
Prompt: {state["case_prompt"]}

## Current Assessment
Level: {current_level} ({level_name})
Red Flags: {state.get("red_flags", [])}
Green Flags: {state.get("green_flags", [])}

## Conversation
{conversation_history}

## Exploration Areas
{areas_summary}

## Areas Covered
{', '.join(state.get("areas_explored", [])) or "None yet"}

## Hidden Facts (share ONLY when earned with hypothesis)
{json.dumps(state.get("hidden_facts", {}), indent=2)}

## Evaluator Guidance (if any)
{state.get("pending_guidance", "None")}

## Your Task
Respond to the candidate's last message. Assess their level and adjust your behavior accordingly.
Remember: DO NOT rescue Level 1-2 candidates. Only help Level 3+ on execution, not thinking.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    response = interviewer_llm.invoke(messages)
    parsed = parse_interviewer_response(response.content)

    # Track token usage
    usage = response.response_metadata.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    new_message = Message(
        role="interviewer",
        content=parsed.get("message", response.content),
        timestamp=datetime.utcnow().isoformat(),
    )

    # Update areas explored
    current_areas = list(state.get("areas_explored", []))
    for area in parsed.get("areas_touched", []):
        if area not in current_areas:
            current_areas.append(area)

    # Extract assessment
    assessment = parsed.get("internal_assessment", {})
    new_level = assessment.get("current_level", state.get("current_level", 0))

    # Map level number to name
    level_names = {
        1: "FAIL",
        2: "WEAK",
        3: "GOOD_NOT_ENOUGH",
        4: "CLEAR_PASS",
        5: "OUTSTANDING"
    }
    new_level_name = level_names.get(new_level, "NOT_ASSESSED")

    # Track level history
    level_history = list(state.get("level_history", []))
    if new_level > 0:
        level_history.append({
            "level": new_level,
            "observation": assessment.get("key_observation", ""),
            "timestamp": datetime.utcnow().isoformat()
        })

    new_phase = parsed.get("current_phase", state.get("current_phase", "ANALYSIS"))

    return {
        "messages": state["messages"] + [new_message],
        "areas_explored": current_areas,
        "current_level": new_level,
        "level_name": new_level_name,
        "level_history": level_history,
        "current_phase": new_phase,
        "pending_guidance": None,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }


def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation."""
    opening = f"""{state["case_prompt"]}

Over to you."""

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
    level_name = state.get("level_name", "NOT_ASSESSED")

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
