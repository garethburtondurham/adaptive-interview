"""
Evaluator Agent - The assessment authority.
Determines candidate level and provides guidance to the interviewer.
Called BEFORE every interviewer response.
"""
from pathlib import Path
from typing import Dict, Any
import json

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import InterviewState
from case_loader import get_case_data
from prompts.evaluator_prompt import get_evaluator_system_prompt

# Initialize LLM
evaluator_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=1024,
)


def parse_evaluator_response(response_text: str) -> Dict[str, Any]:
    """Parse the evaluator's JSON response."""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "current_level": 0,
            "level_name": "PARSE_ERROR",
            "level_justification": "Could not parse evaluation",
            "level_trend": "STABLE",
            "action": "DO_NOT_HELP",
            "interviewer_guidance": "Continue with neutral questions.",
            "data_to_share": None,
            "red_flags": [],
            "green_flags": [],
        }


def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Assess candidate level and provide guidance for the interviewer.

    This is the ONLY assessment authority. Called before every interviewer response.
    """
    # Skip evaluation if no candidate messages yet (opening)
    candidate_messages = [m for m in state["messages"] if m["role"] == "candidate"]
    if not candidate_messages:
        return {
            "current_level": 0,
            "level_name": "NOT_ASSESSED",
            "level_trend": "STABLE",
            "evaluator_action": "DO_NOT_HELP",
            "evaluator_guidance": "Present the case opening and wait for candidate response.",
            "data_to_share": None,
        }

    # Build case data for the dynamic prompt
    case_data = get_case_data(state)
    system_prompt = get_evaluator_system_prompt(case_data)

    # Get conversation context
    recent_messages = state["messages"][-12:]
    conversation = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Get the last candidate message specifically
    last_candidate_msg = candidate_messages[-1]["content"] if candidate_messages else ""

    evaluation_context = f"""## Current Session State

**Conversation so far:**
{conversation}

**Last candidate response (focus your assessment here):**
{last_candidate_msg}

**Assessment history:**
- Previous level: {state.get("current_level", 0)} ({state.get("level_name", 'NOT_ASSESSED')})
- Previous trend: {state.get("level_trend", 'STABLE')}
- Red flags observed so far: {state.get("red_flags_observed", [])}
- Green flags observed so far: {state.get("green_flags_observed", [])}

## Your Task

1. Assess the candidate's current level based on their latest response
2. Determine the action the interviewer should take
3. Provide specific guidance for the interviewer's next response
4. Decide what data (if any) to approve for sharing"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context),
    ]

    response = evaluator_llm.invoke(messages)
    evaluation = parse_evaluator_response(response.content)

    # Track token usage
    usage = response.response_metadata.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    # Update flags (accumulate, don't duplicate)
    red_flags = list(state.get("red_flags_observed", []))
    green_flags = list(state.get("green_flags_observed", []))

    for flag in evaluation.get("red_flags", []):
        if flag and flag not in red_flags:
            red_flags.append(flag)

    for flag in evaluation.get("green_flags", []):
        if flag and flag not in green_flags:
            green_flags.append(flag)

    # Track level history
    level_history = list(state.get("level_history", []))
    new_level = evaluation.get("current_level", state.get("current_level", 0))
    if new_level > 0:
        from datetime import datetime
        level_history.append({
            "level": new_level,
            "trend": evaluation.get("level_trend", "STABLE"),
            "justification": evaluation.get("level_justification", ""),
            "timestamp": datetime.utcnow().isoformat()
        })

    return {
        "current_level": new_level,
        "level_name": evaluation.get("level_name", state.get("level_name", "NOT_ASSESSED")),
        "level_trend": evaluation.get("level_trend", "STABLE"),
        "level_history": level_history,
        "evaluator_action": evaluation.get("action", "DO_NOT_HELP"),
        "evaluator_guidance": evaluation.get("interviewer_guidance", ""),
        "data_to_share": evaluation.get("data_to_share"),
        "red_flags_observed": red_flags,
        "green_flags_observed": green_flags,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }
