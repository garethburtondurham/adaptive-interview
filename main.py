"""
Main entry point for the Adaptive Case Interview System.
Provides a CLI interface for running interviews.
"""
import sys
from case_loader import initialize_interview_state, get_available_cases
from graph import InterviewRunner


def print_separator():
    print("=" * 60)


def print_debug_info(state):
    """Print debug information (would be hidden in production)."""
    print(
        f"[DEBUG] Difficulty: {state['difficulty_level']}/5, "
        f"Phase: {state['current_phase']}, "
        f"Question: {state['current_question_index'] + 1}"
    )
    if state.get("last_evaluator_output"):
        eval_out = state["last_evaluator_output"]
        print(f"[DEBUG] Last Score: {eval_out.get('score', 'N/A')}/5")
        print(f"[DEBUG] Directive: {eval_out.get('directive', 'N/A')}")
    print()


def select_case() -> str:
    """Let user select a case to run."""
    cases = get_available_cases()

    if not cases:
        print("No cases found in the cases/ directory.")
        sys.exit(1)

    print("\nAvailable Cases:")
    print("-" * 40)
    for i, case_id in enumerate(cases, 1):
        print(f"  {i}. {case_id}")
    print()

    while True:
        try:
            choice = input("Select a case (enter number): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(cases):
                return cases[idx]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)


def run_interview(case_id: str, debug: bool = True):
    """Run an interactive interview session."""
    print_separator()
    print("ADAPTIVE CASE INTERVIEW SYSTEM")
    print_separator()
    print(f"\nLoading case: {case_id}\n")

    # Initialize state and runner
    state = initialize_interview_state(case_id)
    runner = InterviewRunner(state)

    # Start the interview
    opening = runner.start()
    print(f"Interviewer: {opening}\n")

    # Conversation loop
    while not runner.is_complete():
        try:
            candidate_input = input("You: ").strip()

            if not candidate_input:
                continue

            if candidate_input.lower() in ["quit", "exit", "q"]:
                print("\nEnding interview early...")
                break

            if candidate_input.lower() == "debug":
                print_debug_info(runner.get_state())
                continue

            if candidate_input.lower() == "scores":
                print("\nScores so far:")
                for score in runner.get_scores():
                    print(f"  {score['question_id']}: {score['score']}/5")
                print()
                continue

            # Process the response
            response = runner.respond(candidate_input)
            print(f"\nInterviewer: {response}\n")

            # Show debug info if enabled
            if debug:
                print_debug_info(runner.get_state())

        except KeyboardInterrupt:
            print("\n\nEnding interview...")
            break

    # Show final results
    print_separator()
    print("INTERVIEW COMPLETE")
    print_separator()

    final_state = runner.get_state()
    final_score = final_state.get("final_score")

    if final_score is not None:
        print(f"\nFinal Score: {final_score}/5")
    else:
        # Calculate if not set
        scores = [qs["score"] for qs in runner.get_scores()]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"\nFinal Score: {avg:.2f}/5")
        else:
            print("\nNo scores recorded.")

    print("\nQuestion Scores:")
    print("-" * 40)
    for qs in runner.get_scores():
        print(f"  {qs['question_id']} ({qs['phase']}): {qs['score']}/5")
        print(f"    Difficulty at time: {qs['difficulty_at_time']}")
        print(f"    Reasoning: {qs['reasoning'][:100]}...")
        print()

    print("\nDifficulty Progression:")
    difficulties = [qs["difficulty_at_time"] for qs in runner.get_scores()]
    if difficulties:
        print(f"  {' -> '.join(map(str, difficulties))}")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Adaptive Case Interview System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands during interview:
  quit, exit, q  - End the interview early
  debug          - Show current state information
  scores         - Show scores so far

Examples:
  python main.py                    # Interactive case selection
  python main.py coffee_profitability   # Run specific case
  python main.py --no-debug         # Hide debug output
        """,
    )
    parser.add_argument("case", nargs="?", help="Case ID to run (optional)")
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Hide debug output during interview",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available cases and exit",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Cases:")
        for case_id in get_available_cases():
            print(f"  - {case_id}")
        return

    # Select or use provided case
    if args.case:
        case_id = args.case
    else:
        case_id = select_case()

    # Run the interview
    run_interview(case_id, debug=not args.no_debug)


if __name__ == "__main__":
    main()
