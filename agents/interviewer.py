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
from prompts.interviewer_prompt import get_interviewer_system_prompt, get_opening_system_prompt

# Initialize LLM (slightly higher temperature for natural conversation)
interviewer_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.4,
    max_tokens=1024,
)


def parse_interviewer_response(response_text: str) -> Dict[str, Any]:
    """Parse the interviewer's JSON response with fallback handling."""
    try:
        # Extract JSON from response (handle markdown code blocks)
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Fallback if parsing fails - treat as plain message
        return {
            "message": response_text,
            "candidate_struggling": False,
            "performance_signals": {"positive": [], "concerns": []},
            "areas_touched": [],
            "current_phase": "ANALYSIS",
        }


def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the interviewer's response to the candidate.
    This is the ONLY agent the candidate interacts with.
    """
    # Check if interview is complete
    if state.get("is_complete"):
        return generate_closing_message(state)

    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message(state)

    # Build context for the interviewer
    system_prompt = get_interviewer_system_prompt()

    # Get recent conversation for context (last 8 messages)
    recent_messages = state["messages"][-8:]
    conversation_history = "\n".join(
        [
            f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
            for m in recent_messages
        ]
    )

    # Get exploration areas for context
    all_areas = get_exploration_areas(state)
    unexplored = get_unexplored_areas(state)

    areas_summary = "\n".join([
        f"- {area['id']}: {area['description']} (key elements: {', '.join(area['key_elements'])})"
        for area in all_areas
    ])

    unexplored_summary = "\n".join([
        f"- {area['id']}: {area['description']}"
        for area in unexplored
    ]) if unexplored else "All areas have been explored"

    # Include hint if evaluator provided one (candidate was struggling)
    hint_context = ""
    if state.get("pending_hint"):
        hint_context = f"""
## Hint to Weave In (candidate was struggling)
Use this hint naturally in your response: {state.get("pending_hint")}
"""

    context = f"""
## Case Information
Title: {state["case_title"]}
Scenario: {state["case_prompt"]}

## Conversation So Far
{conversation_history}

## Exploration Areas for This Case
{areas_summary}

## Areas Not Yet Explored
{unexplored_summary}

## Areas Already Covered
{', '.join(state.get("areas_explored", [])) or "None yet"}

## Key Elements Candidate Has Demonstrated
{', '.join(state.get("key_elements_detected", [])) or "None yet"}

## Hidden Case Facts (share when relevant)
{json.dumps(state["hidden_facts"], indent=2)}
{hint_context}
## Your Task
Respond naturally to the candidate's last message. Continue the conversation, probe their thinking, and guide them through the case. Remember to output valid JSON with your response.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    response = interviewer_llm.invoke(messages)
    parsed = parse_interviewer_response(response.content)

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

    # Track performance signals
    signals = parsed.get("performance_signals", {})
    positive_signals = list(state.get("positive_signals", []))
    concerns = list(state.get("concerns", []))

    for signal in signals.get("positive", []):
        if signal not in positive_signals:
            positive_signals.append(signal)
    for concern in signals.get("concerns", []):
        if concern not in concerns:
            concerns.append(concern)

    # Determine phase
    new_phase = parsed.get("current_phase", state.get("current_phase", "ANALYSIS"))

    return {
        "messages": state["messages"] + [new_message],
        "candidate_struggling": parsed.get("candidate_struggling", False),
        "areas_explored": current_areas,
        "positive_signals": positive_signals,
        "concerns": concerns,
        "current_phase": new_phase,
        "pending_hint": None,  # Clear after using
        "pending_complexity": None,
        "pending_data_reveal": None,
    }


def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation."""
    opening = f"""Welcome! I'm looking forward to working through a case with you today.

Here's the situation: {state["case_prompt"]}

Take a moment to think about this. What are your initial thoughts?"""

    new_message = Message(
        role="interviewer",
        content=opening,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": [new_message],
        "current_phase": "STRUCTURING",
        "candidate_struggling": False,
    }


def generate_closing_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the interview closing."""
    # Assess overall performance based on signals
    positives = len(state.get("positive_signals", []))
    concerns = len(state.get("concerns", []))
    areas_covered = len(state.get("areas_explored", []))

    # Simple heuristic: more positives than concerns is good
    if positives > concerns and areas_covered >= 2:
        score = min(5, 3 + (positives - concerns) * 0.5)
    elif positives == concerns:
        score = 3.0
    else:
        score = max(1, 3 - (concerns - positives) * 0.5)

    closing = """That's a good place to wrap up. Thank you for working through this case with me.

We'll be in touch with next steps soon."""

    new_message = Message(
        role="interviewer",
        content=closing,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": state["messages"] + [new_message],
        "is_complete": True,
        "final_score": round(score, 2),
        "current_phase": "COMPLETE",
    }
