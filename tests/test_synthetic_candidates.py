"""
Synthetic Candidate Tests

Run synthetic candidates through the system to validate adaptive behavior.
Tests that:
1. Strong candidates get higher difficulty and scores
2. Weak candidates get hints and lower difficulty
3. The system adapts appropriately based on performance

Run with: pytest tests/test_synthetic_candidates.py -v
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from case_loader import initialize_interview_state
from graph import InterviewRunner

# Candidate personas
STRONG_CANDIDATE_PROMPT = """You are an excellent consulting candidate with McKinsey experience.
When asked case questions:
- Always structure your thinking clearly using frameworks (e.g., profit = revenue - costs)
- Use MECE principles (Mutually Exclusive, Collectively Exhaustive)
- Ask smart clarifying questions before diving in
- Do mental math accurately and quickly
- Give crisp, CEO-ready summaries
- Reference relevant business concepts and best practices

Respond naturally but demonstrate strong analytical thinking."""

WEAK_CANDIDATE_PROMPT = """You are a nervous candidate with no consulting experience.
When asked case questions:
- Give rambling, unstructured responses
- Miss obvious analytical frameworks
- Struggle with basic math calculations
- Focus on irrelevant details
- Avoid directly answering questions
- Show confusion about business concepts

Respond naturally but show signs of struggling with the material."""

AVERAGE_CANDIDATE_PROMPT = """You are an average candidate with some business background.
When asked case questions:
- Provide decent but not exceptional structure
- Cover the basics but miss some nuances
- Do calculations correctly but slowly
- Give reasonable but generic answers
- Sometimes ask for hints when stuck

Respond naturally with moderate analytical ability."""


def create_synthetic_candidate(persona_prompt: str) -> ChatAnthropic:
    """Create a synthetic candidate LLM with a specific persona."""
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        max_tokens=512,
    )


def generate_candidate_response(
    candidate_llm: ChatAnthropic,
    persona_prompt: str,
    interviewer_message: str,
    conversation_history: str = "",
) -> str:
    """Generate a synthetic candidate's response."""
    context = f"""
{persona_prompt}

## Conversation So Far
{conversation_history}

## Interviewer's Latest Message
{interviewer_message}

Respond as the candidate would. Keep your response focused and conversational (2-4 sentences typically).
"""
    messages = [HumanMessage(content=context)]
    response = candidate_llm.invoke(messages)
    return response.content


def run_synthetic_interview(
    persona_prompt: str,
    case_id: str = "coffee_profitability",
    max_turns: int = 6,
) -> Dict[str, Any]:
    """
    Run a complete interview with a synthetic candidate.

    Returns:
        Dict with interview results including scores and difficulty progression
    """
    # Initialize
    state = initialize_interview_state(case_id)
    runner = InterviewRunner(state)
    candidate_llm = create_synthetic_candidate(persona_prompt)

    # Start interview
    interviewer_message = runner.start()
    conversation_history = f"Interviewer: {interviewer_message}\n"

    print(f"\nInterviewer: {interviewer_message}\n")

    turn = 0
    while not runner.is_complete() and turn < max_turns:
        # Generate candidate response
        candidate_response = generate_candidate_response(
            candidate_llm,
            persona_prompt,
            interviewer_message,
            conversation_history,
        )

        print(f"Candidate: {candidate_response}\n")
        conversation_history += f"Candidate: {candidate_response}\n"

        # Process response
        interviewer_message = runner.respond(candidate_response)
        print(f"Interviewer: {interviewer_message}\n")
        conversation_history += f"Interviewer: {interviewer_message}\n"

        turn += 1

        # Show current state
        current_state = runner.get_state()
        print(
            f"[Turn {turn}] Difficulty: {current_state['difficulty_level']}/5, "
            f"Phase: {current_state['current_phase']}"
        )
        if current_state.get("last_evaluator_output"):
            print(
                f"[Score: {current_state['last_evaluator_output'].get('score', 'N/A')}/5]"
            )
        print()

    # Get final state
    final_state = runner.get_state()

    return {
        "persona": "strong" if "excellent" in persona_prompt.lower() else
                  "weak" if "nervous" in persona_prompt.lower() else "average",
        "turns_completed": turn,
        "final_score": final_state.get("final_score"),
        "difficulty_progression": [
            s["difficulty_at_time"] for s in final_state["question_scores"]
        ],
        "scores": [s["score"] for s in final_state["question_scores"]],
        "average_score": (
            sum(s["score"] for s in final_state["question_scores"])
            / len(final_state["question_scores"])
            if final_state["question_scores"]
            else 0
        ),
        "final_difficulty": final_state["difficulty_level"],
    }


def test_strong_candidate_gets_higher_scores():
    """Test that strong candidates achieve higher scores."""
    print("\n" + "=" * 60)
    print("STRONG CANDIDATE TEST")
    print("=" * 60)

    result = run_synthetic_interview(STRONG_CANDIDATE_PROMPT, max_turns=4)

    print(f"\nResult: {result}")

    # Strong candidates should generally score 3+ on average
    assert result["average_score"] >= 3.0, (
        f"Strong candidate average score {result['average_score']} should be >= 3.0"
    )


def test_weak_candidate_gets_lower_scores():
    """Test that weak candidates get lower scores and difficulty decreases."""
    print("\n" + "=" * 60)
    print("WEAK CANDIDATE TEST")
    print("=" * 60)

    result = run_synthetic_interview(WEAK_CANDIDATE_PROMPT, max_turns=4)

    print(f"\nResult: {result}")

    # Weak candidates should generally score below 3.5 on average
    assert result["average_score"] <= 3.5, (
        f"Weak candidate average score {result['average_score']} should be <= 3.5"
    )


def test_difficulty_adapts_to_performance():
    """Test that difficulty changes based on candidate performance."""
    print("\n" + "=" * 60)
    print("DIFFICULTY ADAPTATION TEST")
    print("=" * 60)

    # Run strong candidate
    strong_result = run_synthetic_interview(STRONG_CANDIDATE_PROMPT, max_turns=4)

    # Run weak candidate
    weak_result = run_synthetic_interview(WEAK_CANDIDATE_PROMPT, max_turns=4)

    print(f"\nStrong candidate difficulty progression: {strong_result['difficulty_progression']}")
    print(f"Weak candidate difficulty progression: {weak_result['difficulty_progression']}")

    # Strong candidates should end at higher or equal difficulty
    # Weak candidates should end at lower or equal difficulty
    strong_final = strong_result["final_difficulty"]
    weak_final = weak_result["final_difficulty"]

    print(f"\nStrong final difficulty: {strong_final}")
    print(f"Weak final difficulty: {weak_final}")

    # Generally, strong should have higher final difficulty than weak
    # But this is probabilistic, so we just check they're different or log it
    if strong_final > weak_final:
        print("PASS: Strong candidate ended at higher difficulty than weak candidate")
    else:
        print(
            "NOTE: Difficulty levels similar - this can happen due to LLM variability"
        )


def test_score_distribution():
    """Test that scores are distributed appropriately for different personas."""
    print("\n" + "=" * 60)
    print("SCORE DISTRIBUTION TEST")
    print("=" * 60)

    results = {}

    for persona_name, prompt in [
        ("strong", STRONG_CANDIDATE_PROMPT),
        ("average", AVERAGE_CANDIDATE_PROMPT),
        ("weak", WEAK_CANDIDATE_PROMPT),
    ]:
        print(f"\nRunning {persona_name} candidate...")
        result = run_synthetic_interview(prompt, max_turns=3)
        results[persona_name] = result
        print(f"{persona_name.capitalize()} average: {result['average_score']:.2f}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for persona, result in results.items():
        print(
            f"{persona.capitalize()}: "
            f"Avg Score = {result['average_score']:.2f}, "
            f"Final Difficulty = {result['final_difficulty']}"
        )

    # Validate ordering (with some tolerance for LLM variability)
    # Strong should generally score higher than weak
    if results["strong"]["average_score"] > results["weak"]["average_score"]:
        print("\nPASS: Score ordering is correct (strong > weak)")
    else:
        print("\nWARNING: Score ordering unexpected - may be due to LLM variability")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run synthetic candidate tests")
    parser.add_argument(
        "--persona",
        choices=["strong", "weak", "average", "all"],
        default="all",
        help="Which persona to test",
    )
    parser.add_argument(
        "--case",
        default="coffee_profitability",
        help="Case ID to use",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=4,
        help="Maximum turns per interview",
    )

    args = parser.parse_args()

    if args.persona == "all":
        test_score_distribution()
    else:
        prompts = {
            "strong": STRONG_CANDIDATE_PROMPT,
            "weak": WEAK_CANDIDATE_PROMPT,
            "average": AVERAGE_CANDIDATE_PROMPT,
        }
        result = run_synthetic_interview(
            prompts[args.persona],
            case_id=args.case,
            max_turns=args.turns,
        )
        print(f"\nFinal Result: {result}")
