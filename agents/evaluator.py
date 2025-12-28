"""
Evaluator Agent - Assesses candidate level and provides guidance.
Called periodically for detailed assessment.
"""
from typing import Dict, Any
import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import InterviewState
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
            "action": "DO_NOT_HELP",
            "interviewer_guidance": None,
            "data_to_share": None,
            "red_flags": [],
            "green_flags": [],
        }


def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Detailed assessment of candidate level.
    """
    # Get conversation context
    recent_messages = state["messages"][-10:]
    conversation = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    system_prompt = get_evaluator_system_prompt()

    evaluation_context = f"""
## Case
Title: {state["case_title"]}
Opening: {state["opening"]}

## Full Conversation
{conversation}

## Facts (for reference)
{json.dumps(state.get("facts", {}), indent=2)}

## Root Cause (what good looks like)
{state.get("root_cause", "")}

## Current Assessment
Level: {state.get("current_level", 0)} ({state.get("level_name", 'NOT_ASSESSED')})
Red Flags so far: {state.get("red_flags_observed", [])}
Green Flags so far: {state.get("green_flags_observed", [])}

## Your Task
Assess the candidate's current level based on the full conversation.
Determine what action the interviewer should take next.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context),
    ]

    response = evaluator_llm.invoke(messages)
    evaluation = parse_evaluator_response(response.content)

    # Track token usage
    usage = response.response_metadata.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    # Update flags
    red_flags = list(state.get("red_flags_observed", []))
    green_flags = list(state.get("green_flags_observed", []))

    for flag in evaluation.get("red_flags", []):
        if flag and flag not in red_flags:
            red_flags.append(flag)

    for flag in evaluation.get("green_flags", []):
        if flag and flag not in green_flags:
            green_flags.append(flag)

    return {
        "current_level": evaluation.get("current_level", state.get("current_level", 0)),
        "level_name": evaluation.get("level_name", state.get("level_name", "NOT_ASSESSED")),
        "red_flags_observed": red_flags,
        "green_flags_observed": green_flags,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }
