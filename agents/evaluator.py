"""
Evaluator Agent - Assesses struggling candidates and provides guidance.
This agent is HIDDEN from the candidate and only called when needed.
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
    temperature=0.1,
    max_tokens=1024,
)


def parse_evaluator_response(response_text: str) -> Dict[str, Any]:
    """Parse the evaluator's JSON response with fallback handling."""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "struggle_type": "B_REDIRECT",
            "assessment": "Unable to parse evaluation",
            "recommendation": "OBSERVE",
            "suggested_prompt": None,
            "performance_note": "Evaluation parsing failed",
            "should_provide_data": False,
        }


def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Assess the struggling candidate and provide guidance to the interviewer.
    Only called when interviewer flags genuine struggle.
    """
    # Get conversation context
    recent_messages = state["messages"][-8:]
    conversation = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Get exploration areas for context
    areas = state.get("exploration_areas", [])
    areas_context = "\n".join([
        f"- {area['id']}: {area['description']} | Key elements: {', '.join(area['key_elements'])}"
        for area in areas
    ])

    system_prompt = get_evaluator_system_prompt()

    evaluation_context = f"""
## Case Information
Title: {state["case_title"]}
Objective: {state["case_prompt"]}

## Current Phase
{state.get("current_phase", "ANALYSIS")}

## Conversation History
{conversation}

## Case Structure
{areas_context}

## Hidden Facts (for your reference)
{json.dumps(state.get("hidden_facts", {}), indent=2)}

## Progress So Far
Areas explored: {', '.join(state.get("areas_explored", [])) or "None yet"}

## Your Task
The interviewer has flagged that the candidate is struggling. Assess the situation and provide guidance.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context),
    ]

    response = evaluator_llm.invoke(messages)
    evaluation = parse_evaluator_response(response.content)

    # Only provide a hint if recommendation is to help
    pending_hint = None
    if evaluation.get("recommendation") in ["LIGHT_PROMPT", "REDIRECT"]:
        pending_hint = evaluation.get("suggested_prompt")

    return {
        "pending_hint": pending_hint,
        "last_evaluator_output": {
            "struggle_type": evaluation.get("struggle_type"),
            "assessment": evaluation.get("assessment"),
            "recommendation": evaluation.get("recommendation"),
            "performance_note": evaluation.get("performance_note"),
        },
    }
