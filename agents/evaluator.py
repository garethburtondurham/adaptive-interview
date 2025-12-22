"""
Evaluator Agent - Scores responses and determines next actions.
This agent is HIDDEN from the candidate.
"""
from typing import Dict, Any
import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from state import InterviewState, QuestionScore, Directive
from case_loader import get_current_question
from prompts.evaluator_prompt import get_evaluator_system_prompt

# Initialize LLM (use Claude for evaluation - more reliable structured output)
evaluator_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.1,  # Low temperature for consistent scoring
    max_tokens=1024,
)


def parse_evaluator_response(response_text: str) -> Dict[str, Any]:
    """Parse the evaluator's JSON response with fallback handling."""
    try:
        # Extract JSON from response (handle markdown code blocks)
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Fallback if parsing fails
        return {
            "score": 3,
            "reasoning": "Could not parse evaluation, defaulting to average",
            "key_elements_detected": [],
            "directive": Directive.PROCEED_STANDARD.value,
            "hint_if_needed": None,
            "complexity_addition": None,
            "data_to_reveal": None,
        }


def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluate the candidate's last response and determine next action.
    This agent is HIDDEN from the candidate.
    """
    # Get the last candidate message
    candidate_messages = [m for m in state["messages"] if m["role"] == "candidate"]
    if not candidate_messages:
        # No response yet, just starting
        return {"next_directive": Directive.PROCEED_STANDARD.value}

    last_response = candidate_messages[-1]["content"]
    current_question = get_current_question(state)

    if current_question is None:
        # No more questions
        return {"next_directive": Directive.END_INTERVIEW.value, "is_complete": True}

    # Build the evaluation prompt
    system_prompt = get_evaluator_system_prompt()

    evaluation_context = f"""
## Current Phase
{state["current_phase"]}

## Current Difficulty Level
{state["difficulty_level"]} / 5

## Question Asked
{current_question.get("prompt", "Initial case presentation")}

## Rubric for This Question
{json.dumps(current_question.get("rubric", {}), indent=2)}

## Key Elements to Detect
{json.dumps(current_question.get("key_elements", []), indent=2)}

## Hidden Case Facts (for reference)
{json.dumps(state["hidden_facts"], indent=2)}

## Candidate's Response
{last_response}

## Previous Scores in This Interview
{json.dumps(state["question_scores"][-3:], indent=2) if state["question_scores"] else "None yet"}
"""

    # Call the LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context),
    ]

    response = evaluator_llm.invoke(messages)
    evaluation = parse_evaluator_response(response.content)

    # Record the score
    new_score = QuestionScore(
        question_id=f"q_{state['current_question_index']}",
        phase=state["current_phase"],
        score=evaluation.get("score", 3),
        reasoning=evaluation.get("reasoning", ""),
        key_elements_detected=evaluation.get("key_elements_detected", []),
        difficulty_at_time=state["difficulty_level"],
    )

    # Calculate new difficulty level
    score = evaluation.get("score", 3)
    current_diff = state["difficulty_level"]

    if score >= 4:
        new_difficulty = min(5, current_diff + 1)
    elif score <= 2:
        new_difficulty = max(1, current_diff - 1)
    else:
        new_difficulty = current_diff

    # Determine if we should move to next question
    directive = evaluation.get("directive", Directive.PROCEED_STANDARD.value)
    next_question_index = state["current_question_index"]
    next_phase = state["current_phase"]

    if directive in [
        Directive.PROCEED_STANDARD.value,
        Directive.ADD_COMPLEXITY.value,
        Directive.MOVE_TO_NEXT_PHASE.value,
    ]:
        next_question_index += 1
        # Check if next question exists and update phase
        if next_question_index < len(state["question_sequence"]):
            next_phase = state["question_sequence"][next_question_index].get(
                "phase", next_phase
            )

    return {
        "question_scores": state["question_scores"] + [new_score],
        "difficulty_level": new_difficulty,
        "current_question_index": next_question_index,
        "current_phase": next_phase,
        "last_evaluator_output": evaluation,
        "next_directive": directive,
        "pending_hint": evaluation.get("hint_if_needed"),
        "pending_complexity": evaluation.get("complexity_addition"),
        "pending_data_reveal": evaluation.get("data_to_reveal"),
    }
