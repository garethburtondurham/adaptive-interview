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
    level = state.get("current_level", 0)
    level_name = state.get("level_name", "NOT_ASSESSED")
    trend = state.get("level_trend", "STABLE")
    phase = state.get("current_phase", "UNKNOWN")

    print(f"[DEBUG] Level: {level}/5 ({level_name}), Trend: {trend}, Phase: {phase}")

    red_flags = state.get("red_flags_observed", [])
    green_flags = state.get("green_flags_observed", [])

    if red_flags:
        print(f"[DEBUG] Red Flags: {red_flags}")
    if green_flags:
        print(f"[DEBUG] Green Flags: {green_flags}")

    # Show level history if available
    level_history = state.get("level_history", [])
    if level_history and len(level_history) > 0:
        latest = level_history[-1]
        print(f"[DEBUG] Latest thinking: {latest.get('thinking', 'N/A')[:100]}...")

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

            if candidate_input.lower() == "level":
                level, level_name = runner.get_current_level()
                print(f"\nCurrent Level: {level}/5 ({level_name})\n")
                continue

            if candidate_input.lower() == "flags":
                red_flags, green_flags = runner.get_flags()
                print("\nRed Flags Observed:")
                for flag in red_flags:
                    print(f"  - {flag}")
                print("\nGreen Flags Observed:")
                for flag in green_flags:
                    print(f"  - {flag}")
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
    final_level = final_state.get("current_level", 0)
    final_level_name = final_state.get("level_name", "NOT_ASSESSED")

    print(f"\nFinal Assessment: Level {final_level}/5 ({final_level_name})")

    # Show flags summary
    red_flags = final_state.get("red_flags_observed", [])
    green_flags = final_state.get("green_flags_observed", [])

    if red_flags:
        print("\nRed Flags Observed:")
        print("-" * 40)
        for flag in red_flags:
            print(f"  - {flag}")

    if green_flags:
        print("\nGreen Flags Observed:")
        print("-" * 40)
        for flag in green_flags:
            print(f"  - {flag}")

    # Show level progression
    level_history = final_state.get("level_history", [])
    if level_history:
        print("\nLevel Progression:")
        print("-" * 40)
        levels = [h["level"] for h in level_history]
        print(f"  {' -> '.join(map(str, levels))}")

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
  level          - Show current assessment level
  flags          - Show observed red/green flags

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
