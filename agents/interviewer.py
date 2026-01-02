"""
Interviewer Agent - Candidate-facing conversation handler.

Executes the interview methodology and follows evaluator guidance.
This is the ONLY agent the candidate interacts with.

The interviewer is a "Method Actor" - same core capabilities, different script.
When an InterviewSpec is present, behavior is adapted by the heuristics.
"""
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import json

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import (
    InterviewState,
    Message,
    has_spec,
    get_heuristics,
    get_context_packet,
    get_current_phase_config,
)
from prompts.prompt_builder import build_interviewer_prompt, build_opening_message

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

    When an InterviewSpec is present, uses heuristics from the spec.
    Otherwise, uses legacy case interview behavior.
    """
    # Check if interview is complete
    if state.get("is_complete"):
        return generate_closing_message(state)

    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message_node(state)

    # Build the system prompt (spec-driven or legacy)
    system_prompt = build_interviewer_prompt(state)

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

    # Get manager directive if present
    manager_context = ""
    manager_directive = state.get("manager_directive")
    if manager_directive:
        focus_area = manager_directive.get("focus_area", "")
        urgency = manager_directive.get("urgency", "normal")
        undercovered = manager_directive.get("undercovered_competencies", [])

        if focus_area or undercovered:
            manager_context = f"""
## Manager Guidance
**Focus Area:** {focus_area if focus_area else 'None specific'}
**Urgency:** {urgency}
**Competencies needing more signal:** {', '.join(undercovered) if undercovered else 'None'}
"""

    context = f"""## Evaluator Guidance

**Action:** {evaluator_action}
**Specific guidance:** {evaluator_guidance}
**Data approved to share:** {data_to_share if data_to_share else "None - do not share data unless candidate earns it"}
{manager_context}
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


def generate_opening_message_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the initial message to start the interview.

    Adapts to interview type:
    - Case: Present the case prompt
    - First Round: Warm greeting and context
    - Technical: Present the problem
    """
    if has_spec(state):
        return _generate_spec_opening(state)
    else:
        return _generate_legacy_opening(state)


def _generate_spec_opening(state: InterviewState) -> Dict[str, Any]:
    """Generate opening from spec."""

    context_packet = get_context_packet(state) or {}
    heuristics = get_heuristics(state) or {}
    packet_type = context_packet.get("packet_type", "")
    spec = state.get("interview_spec", {})

    # Get the first phase
    phases = spec.get("phases", [])
    first_phase = phases[0]["id"] if phases else "opening"

    # Build the opening based on interview type
    if packet_type == "case_study":
        opening = _build_case_opening(context_packet, heuristics)
    elif packet_type == "cv_screen":
        opening = _build_cv_opening(context_packet, heuristics)
    elif packet_type == "technical_problem":
        opening = _build_technical_opening(context_packet, heuristics)
    else:
        # Fallback
        opening = build_opening_message(state)

    new_message = Message(
        role="interviewer",
        content=opening,
        timestamp=datetime.utcnow().isoformat(),
    )

    return {
        "messages": [new_message],
        "current_phase": first_phase.upper(),
    }


def _build_case_opening(context_packet: Dict[str, Any], heuristics: Dict[str, Any]) -> str:
    """Build opening for case interview."""

    case_study = context_packet.get("case_study", {})
    case_prompt = case_study.get("case_prompt", "")

    # Remove trailing "Over to you." if present
    case_prompt = case_prompt.replace("\n\nOver to you.", "").replace("Over to you.", "").strip()

    # Add intro based on heuristics
    opening_style = heuristics.get("opening_style", "")

    if "give them a moment" in opening_style.lower():
        intro = """Take a moment to gather your thoughts. Feel free to ask any clarifying questions, and when you're ready, share how you'd like to approach this.

Over to you."""
    else:
        intro = "Over to you."

    return f"{case_prompt}\n\n{intro}"


def _build_cv_opening(context_packet: Dict[str, Any], heuristics: Dict[str, Any]) -> str:
    """Build opening for first-round screening."""

    cv_screen = context_packet.get("cv_screen", {})
    role_title = cv_screen.get("role_title", "this role")

    opening_style = heuristics.get("opening_style", "")

    # Build a warm, conversational opening
    opening = f"""Thanks for joining me today. I've had a chance to review your background, and I'm looking forward to learning more about your experience.

We'll spend about 30 minutes today discussing your background and the {role_title} position. I'd love to hear about what you've been working on and what brings you to this opportunity.

Let's start with your most recent role. Tell me about what you've been doing there."""

    return opening


def _build_technical_opening(context_packet: Dict[str, Any], heuristics: Dict[str, Any]) -> str:
    """Build opening for technical interview."""

    tech = context_packet.get("technical_problem", {})
    problem = tech.get("problem_statement", "")

    opening_style = heuristics.get("opening_style", "")

    intro = """Thanks for joining. Let me share a problem with you.

Take a moment to read through it, and feel free to ask any clarifying questions before you start.

---

"""

    return f"{intro}{problem}"


def _generate_legacy_opening(state: InterviewState) -> Dict[str, Any]:
    """Generate opening for legacy case interviews (backward compatibility)."""

    opening = state.get("opening", "")

    # Remove trailing "Over to you." if present (we'll add our own ending)
    opening = opening.replace("\n\nOver to you.", "").replace("Over to you.", "").strip()

    # Brief expectations after the case
    intro = """Take a moment to gather your thoughts. Feel free to ask any clarifying questions, and when you're ready, share how you'd like to approach this. There's no single right answer - I'm interested in your thinking.

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
    """
    Generate the interview closing.

    Adapts to interview type based on heuristics.
    """
    heuristics = get_heuristics(state) or {}
    closing_style = heuristics.get("closing_style", "")

    # Default closings by type
    if has_spec(state):
        spec = state.get("interview_spec", {})
        interview_type = spec.get("interview_type", "")

        if interview_type == "first_round":
            closing = "That's been really helpful - thank you for sharing your background with me. Do you have any questions for me about the role or the company before we wrap up?"
        elif interview_type == "technical":
            closing = "That's a good stopping point. Thanks for working through this problem with me. Let's briefly discuss what you'd do if you had more time."
        else:
            closing = "That's a good place to wrap up. Thank you for working through this case with me."
    else:
        closing = "That's a good place to wrap up. Thank you for working through this case with me."

    # Use custom closing style if provided
    if closing_style and "thank them" in closing_style.lower():
        # Keep the default, it includes thanks
        pass

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
