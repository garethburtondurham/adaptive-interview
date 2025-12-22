"""
Streamlit Web Interface for the Adaptive Case Interview System.

Run with: streamlit run ui/streamlit_app.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import streamlit as st
from case_loader import initialize_interview_state, get_available_cases
from graph import InterviewRunner

# Page configuration
st.set_page_config(
    page_title="Case Interview System",
    page_icon="💼",
    layout="wide",
)

# Initialize session state
if "runner" not in st.session_state:
    st.session_state.runner = None
if "started" not in st.session_state:
    st.session_state.started = False
if "messages" not in st.session_state:
    st.session_state.messages = []


def reset_interview():
    """Reset the interview state."""
    st.session_state.runner = None
    st.session_state.started = False
    st.session_state.messages = []


# Sidebar for controls and debug info
with st.sidebar:
    st.title("Interview Controls")

    if st.session_state.started and st.session_state.runner:
        state = st.session_state.runner.get_state()

        # Status indicators
        st.subheader("Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Phase", state.get("current_phase", "N/A"))
        with col2:
            areas_explored = len(state.get("areas_explored", []))
            total_areas = len(state.get("exploration_areas", []))
            st.metric("Progress", f"{areas_explored}/{total_areas}")

        # Count exchanges
        candidate_msgs = [m for m in state.get("messages", []) if m["role"] == "candidate"]
        st.metric("Exchanges", len(candidate_msgs))

        # Progress bar based on areas explored
        if total_areas > 0:
            progress = min(areas_explored / total_areas, 1.0)
            st.progress(progress, text=f"Areas Explored: {areas_explored}/{total_areas}")

        # Areas explored section
        with st.expander("Areas Explored", expanded=False):
            explored = state.get("areas_explored", [])
            if explored:
                for area in explored:
                    st.write(f"✓ {area}")
            else:
                st.write("No areas explored yet")

        # Performance signals section
        with st.expander("Performance Signals", expanded=False):
            positives = state.get("positive_signals", [])
            concerns = state.get("concerns", [])

            if positives:
                st.write("**Strengths:**")
                for signal in positives:
                    st.write(f"✓ {signal}")

            if concerns:
                st.write("**Areas to Watch:**")
                for concern in concerns:
                    st.write(f"⚠ {concern}")

            if not positives and not concerns:
                st.write("No signals recorded yet")

        # Debug section (collapsible)
        with st.expander("Debug Info", expanded=False):
            st.write(f"**Candidate Struggling:** {state.get('candidate_struggling', False)}")
            if state.get("last_evaluator_output"):
                st.write("**Last Evaluator Output:**")
                st.json(state["last_evaluator_output"])

        st.divider()

        # Reset button
        if st.button("Reset Interview", type="secondary", use_container_width=True):
            reset_interview()
            st.rerun()

# Main content area
st.title("Adaptive Case Interview")

# Case selection (before interview starts)
if not st.session_state.started:
    st.markdown("""
    Welcome to the Adaptive Case Interview System. This AI-powered tool conducts
    case study interviews similar to management consulting firms.

    **How it works:**
    - Have a natural conversation about the case
    - The interviewer adapts based on your responses
    - If you get stuck, the system provides subtle guidance
    - Focus on your thinking process, not frameworks
    """)

    st.divider()

    # Case selection
    cases = get_available_cases()

    if not cases:
        st.error("No cases found. Please add case files to the cases/ directory.")
    else:
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_case = st.selectbox(
                "Select a case:",
                cases,
                format_func=lambda x: x.replace("_", " ").title(),
            )

        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("Start Interview", type="primary", use_container_width=True):
                # Initialize the interview
                state = initialize_interview_state(selected_case)
                st.session_state.runner = InterviewRunner(state)
                st.session_state.started = True

                # Get opening message
                opening = st.session_state.runner.start()
                st.session_state.messages = [
                    {"role": "interviewer", "content": opening}
                ]
                st.rerun()

else:
    # Interview in progress
    runner = st.session_state.runner
    state = runner.get_state()

    # Check if complete
    if runner.is_complete():
        st.success("Interview Complete!")

        # Show final score
        final_score = state.get("final_score")
        if final_score:
            st.metric("Final Score", f"{final_score:.1f}/5")

        # Show summary
        st.subheader("Performance Summary")

        col1, col2, col3 = st.columns(3)
        with col1:
            areas = state.get("areas_explored", [])
            st.metric("Areas Explored", len(areas))
        with col2:
            positives = state.get("positive_signals", [])
            st.metric("Strengths Shown", len(positives))
        with col3:
            msgs = [m for m in state.get("messages", []) if m["role"] == "candidate"]
            st.metric("Total Exchanges", len(msgs))

        # Performance Summary
        positives = state.get("positive_signals", [])
        concerns = state.get("concerns", [])

        if positives:
            st.subheader("Strengths Demonstrated")
            for signal in positives:
                st.write(f"✓ {signal}")

        if concerns:
            st.subheader("Areas for Development")
            for concern in concerns:
                st.write(f"⚠ {concern}")

        # Areas breakdown
        st.subheader("Topics Covered")
        for area in state.get("areas_explored", []):
            st.write(f"• {area}")

        if st.button("Start New Interview", type="primary"):
            reset_interview()
            st.rerun()

    else:
        # Display conversation
        st.subheader(f"Case: {state['case_title']}")

        # Chat container
        chat_container = st.container()

        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "interviewer":
                    with st.chat_message("assistant", avatar="👔"):
                        st.write(msg["content"])
                else:
                    with st.chat_message("user", avatar="👤"):
                        st.write(msg["content"])

        # Input area
        if prompt := st.chat_input("Your response..."):
            # Add user message to display
            st.session_state.messages.append({"role": "candidate", "content": prompt})

            # Get interviewer response
            with st.spinner("Thinking..."):
                response = runner.respond(prompt)

            # Add interviewer response to display
            st.session_state.messages.append(
                {"role": "interviewer", "content": response}
            )

            # Rerun to update the display
            st.rerun()

# Footer
st.divider()
st.caption(
    "Adaptive Case Interview System | "
    "Powered by Claude AI | "
    "Built with LangGraph and Streamlit"
)
