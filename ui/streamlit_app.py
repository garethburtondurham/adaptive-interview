"""
Streamlit Web Interface for the Adaptive Case Interview System.

Run with: streamlit run ui/streamlit_app.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
            st.metric("Difficulty", f"{state['difficulty_level']}/5")
        with col2:
            st.metric("Phase", state["current_phase"])

        st.metric("Questions Answered", len(state["question_scores"]))

        # Progress bar
        total_qs = len(state["question_sequence"])
        current_q = state["current_question_index"]
        progress = min(current_q / total_qs, 1.0) if total_qs > 0 else 0
        st.progress(progress, text=f"Progress: {current_q}/{total_qs}")

        # Scores section (collapsible)
        with st.expander("Question Scores", expanded=False):
            for qs in state["question_scores"]:
                st.write(f"**{qs['question_id']}** ({qs['phase']})")
                st.write(f"Score: {qs['score']}/5 | Difficulty: {qs['difficulty_at_time']}")
                st.caption(qs["reasoning"][:150] + "...")
                st.divider()

        # Debug section (collapsible)
        with st.expander("Debug Info", expanded=False):
            if state.get("last_evaluator_output"):
                eval_out = state["last_evaluator_output"]
                st.json(eval_out)

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
    - The system adapts difficulty based on your performance
    - Each response is scored against specific rubrics
    - Strong candidates get harder follow-ups
    - Struggling candidates receive helpful hints
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
            st.metric("Final Score", f"{final_score}/5")

        # Show summary
        st.subheader("Performance Summary")

        scores = runner.get_scores()
        if scores:
            # Score distribution
            score_values = [s["score"] for s in scores]
            avg_score = sum(score_values) / len(score_values)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Score", f"{avg_score:.1f}/5")
            with col2:
                st.metric("Questions Answered", len(scores))
            with col3:
                difficulties = [s["difficulty_at_time"] for s in scores]
                st.metric("Max Difficulty Reached", max(difficulties))

            # Detailed scores
            st.subheader("Question-by-Question Breakdown")
            for qs in scores:
                with st.expander(f"{qs['question_id']} - Score: {qs['score']}/5"):
                    st.write(f"**Phase:** {qs['phase']}")
                    st.write(f"**Difficulty at time:** {qs['difficulty_at_time']}")
                    st.write(f"**Reasoning:** {qs['reasoning']}")
                    if qs["key_elements_detected"]:
                        st.write("**Key elements detected:**")
                        for elem in qs["key_elements_detected"]:
                            st.write(f"  - {elem}")

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
