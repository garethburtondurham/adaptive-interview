"""
Evaluator Agent - The assessment authority.

Determines candidate level and provides guidance to the interviewer.
Called BEFORE every interviewer response.

When an InterviewSpec is present, scores each competency independently
for multi-dimensional assessment.
"""
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import (
    InterviewState,
    CompetencyScore,
    has_spec,
    get_heuristics,
    create_empty_competency_score,
    get_overall_level,
    get_level_name,
)
from prompts.evaluator_prompt_builder import build_evaluator_prompt

# Initialize LLM
evaluator_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=2048,  # Increased for multi-competency output
)


def parse_evaluator_response(response_text: str, is_spec_driven: bool = False) -> Dict[str, Any]:
    """Parse the evaluator's JSON response."""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        parsed = json.loads(text.strip())

        # Validate required fields based on mode
        if is_spec_driven:
            if "competency_scores" not in parsed:
                parsed["competency_scores"] = {}
            if "action" not in parsed:
                parsed["action"] = "DO_NOT_HELP"
        else:
            # Legacy format
            if "current_level" not in parsed:
                parsed["current_level"] = 0

        return parsed

    except json.JSONDecodeError:
        # Fallback response
        if is_spec_driven:
            return {
                "competency_scores": {},
                "overall_assessment": "Could not parse evaluation",
                "action": "DO_NOT_HELP",
                "interviewer_guidance": "Continue with neutral questions.",
                "data_to_share": None,
                "focus_next": None,
            }
        else:
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
    Assess candidate performance and provide guidance for the interviewer.

    This is the ONLY assessment authority. Called before every interviewer response.

    When an InterviewSpec is present, returns multi-dimensional competency scores.
    Otherwise, uses legacy single-score format for backward compatibility.
    """
    # Skip evaluation if no candidate messages yet (opening)
    candidate_messages = [m for m in state["messages"] if m["role"] == "candidate"]
    if not candidate_messages:
        return _get_initial_evaluation_state(state)

    # Build the system prompt (spec-driven or legacy)
    system_prompt = build_evaluator_prompt(state)

    # Get conversation context
    recent_messages = state["messages"][-12:]
    conversation = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])

    # Get the last candidate message specifically
    last_candidate_msg = candidate_messages[-1]["content"] if candidate_messages else ""

    # Build assessment history context
    if has_spec(state):
        assessment_history = _build_competency_history_context(state)
    else:
        assessment_history = _build_legacy_history_context(state)

    evaluation_context = f"""## Current Session State

**Conversation so far:**
{conversation}

**Last candidate response (focus your assessment here):**
{last_candidate_msg}

{assessment_history}

## Your Task

1. Assess the candidate's performance on each competency based on their latest response
2. Determine the action the interviewer should take
3. Provide specific guidance for the interviewer's next response
4. Decide what data (if any) to approve for sharing"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context),
    ]

    response = evaluator_llm.invoke(messages)

    # Track token usage
    usage = response.response_metadata.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    # Parse and process based on mode
    if has_spec(state):
        return _process_spec_driven_evaluation(state, response.content, tokens_used)
    else:
        return _process_legacy_evaluation(state, response.content, tokens_used)


def _get_initial_evaluation_state(state: InterviewState) -> Dict[str, Any]:
    """Return initial evaluation state when no candidate messages yet."""

    base_state = {
        "current_level": 0,
        "level_name": "NOT_ASSESSED",
        "level_trend": "STABLE",
        "evaluator_action": "DO_NOT_HELP",
        "evaluator_guidance": "Present the opening and wait for candidate response.",
        "data_to_share": None,
    }

    # Initialize competency scores if spec present
    if has_spec(state):
        spec = state.get("interview_spec", {})
        competency_scores = {}
        for comp in spec.get("competencies", []):
            comp_id = comp.get("competency_id", "")
            competency_scores[comp_id] = create_empty_competency_score(comp_id)
        base_state["competency_scores"] = competency_scores

    return base_state


def _build_competency_history_context(state: InterviewState) -> str:
    """Build assessment history context for spec-driven evaluation."""

    comp_scores = state.get("competency_scores", {})
    if not comp_scores:
        return "**Assessment history:** No previous assessment."

    lines = ["**Previous Competency Scores:**"]
    for comp_id, score in comp_scores.items():
        level = score.get("current_level", 0)
        confidence = score.get("confidence", "low")
        if level > 0:
            lines.append(f"- {comp_id}: Level {level} ({confidence} confidence)")
        else:
            lines.append(f"- {comp_id}: Not yet assessed")

    return "\n".join(lines)


def _build_legacy_history_context(state: InterviewState) -> str:
    """Build assessment history context for legacy evaluation."""

    return f"""**Assessment history:**
- Previous level: {state.get("current_level", 0)} ({state.get("level_name", 'NOT_ASSESSED')})
- Previous trend: {state.get("level_trend", 'STABLE')}
- Red flags observed so far: {state.get("red_flags_observed", [])}
- Green flags observed so far: {state.get("green_flags_observed", [])}"""


def _process_spec_driven_evaluation(
    state: InterviewState,
    response_content: str,
    tokens_used: int
) -> Dict[str, Any]:
    """Process evaluation response for spec-driven interviews."""

    evaluation = parse_evaluator_response(response_content, is_spec_driven=True)
    spec = state.get("interview_spec", {})

    # Update competency scores
    competency_scores = dict(state.get("competency_scores", {}))
    new_comp_scores = evaluation.get("competency_scores", {})

    # Get exchange count for history
    exchange_count = len([m for m in state.get("messages", []) if m["role"] == "candidate"])
    timestamp = datetime.utcnow().isoformat()

    # Aggregate flags
    all_red_flags = list(state.get("red_flags_observed", []))
    all_green_flags = list(state.get("green_flags_observed", []))

    for comp_id, score_data in new_comp_scores.items():
        if comp_id not in competency_scores:
            competency_scores[comp_id] = create_empty_competency_score(comp_id)

        existing = competency_scores[comp_id]
        new_level = score_data.get("level", 0)
        evidence = score_data.get("evidence", "")
        flags = score_data.get("flags", [])

        # Update level if we have a new assessment
        if new_level > 0:
            # Track history if level changed
            if new_level != existing.get("current_level", 0):
                history = list(existing.get("level_history", []))
                history.append({
                    "level": new_level,
                    "exchange": exchange_count,
                    "reason": evidence,
                    "timestamp": timestamp
                })
                existing["level_history"] = history

            existing["current_level"] = new_level

            # Add evidence
            if evidence:
                existing_evidence = list(existing.get("evidence", []))
                existing_evidence.append(evidence)
                existing["evidence"] = existing_evidence[-5:]  # Keep last 5

            # Update confidence based on evidence count
            evidence_count = len(existing.get("evidence", []))
            if evidence_count >= 3:
                existing["confidence"] = "high"
            elif evidence_count >= 2:
                existing["confidence"] = "medium"
            else:
                existing["confidence"] = "low"

            # Process flags
            for flag in flags:
                if flag.startswith("RED:") or "red" in flag.lower():
                    clean_flag = flag.replace("RED:", "").strip()
                    if clean_flag not in existing.get("red_flags_observed", []):
                        existing.setdefault("red_flags_observed", []).append(clean_flag)
                    if clean_flag not in all_red_flags:
                        all_red_flags.append(clean_flag)
                elif flag.startswith("GREEN:") or "green" in flag.lower():
                    clean_flag = flag.replace("GREEN:", "").strip()
                    if clean_flag not in existing.get("green_flags_observed", []):
                        existing.setdefault("green_flags_observed", []).append(clean_flag)
                    if clean_flag not in all_green_flags:
                        all_green_flags.append(clean_flag)

        competency_scores[comp_id] = existing

    # Calculate overall level from competency scores
    overall_level = get_overall_level(competency_scores, spec)
    level_name = get_level_name(overall_level)

    # Determine trend
    prev_level = state.get("current_level", 0)
    if overall_level > prev_level:
        trend = "UP"
    elif overall_level < prev_level:
        trend = "DOWN"
    else:
        trend = "STABLE"

    # Track level history
    level_history = list(state.get("level_history", []))
    if overall_level > 0:
        level_history.append({
            "level": overall_level,
            "trend": trend,
            "justification": evaluation.get("overall_assessment", ""),
            "timestamp": timestamp
        })

    return {
        "competency_scores": competency_scores,
        "current_level": overall_level,
        "level_name": level_name,
        "level_trend": trend,
        "level_history": level_history,
        "evaluator_action": evaluation.get("action", "DO_NOT_HELP"),
        "evaluator_guidance": evaluation.get("interviewer_guidance", ""),
        "data_to_share": evaluation.get("data_to_share"),
        "red_flags_observed": all_red_flags,
        "green_flags_observed": all_green_flags,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }


def _process_legacy_evaluation(
    state: InterviewState,
    response_content: str,
    tokens_used: int
) -> Dict[str, Any]:
    """Process evaluation response for legacy case interviews."""

    evaluation = parse_evaluator_response(response_content, is_spec_driven=False)

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
