"""
Streamlit Web Interface for the Adaptive Case Interview System.

Run with: streamlit run ui/streamlit_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import streamlit as st
from case_loader import initialize_interview_state, get_available_cases
from graph import InterviewRunner

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
    st.session_state.runner = None
    st.session_state.started = False
    st.session_state.messages = []


def get_level_color(level: int) -> str:
    """Get color for assessment level."""
    colors = {
        0: "gray",
        1: "red",
        2: "orange",
        3: "yellow",
        4: "green",
        5: "blue"
    }
    return colors.get(level, "gray")


def get_level_emoji(level: int) -> str:
    """Get emoji for assessment level."""
    emojis = {
        0: "⏳",
        1: "❌",
        2: "⚠️",
        3: "📊",
        4: "✅",
        5: "⭐"
    }
    return emojis.get(level, "⏳")


# Sidebar
with st.sidebar:
    st.title("Interview Controls")

    # Credits section
    with st.expander("Usage & Credits", expanded=False):
        if st.session_state.started and st.session_state.runner:
            runner_state = st.session_state.runner.get_state()
            session_tokens = runner_state.get("total_tokens", 0)
            estimated_cost = (session_tokens / 1_000_000) * 9
            st.metric("Session Tokens", f"{session_tokens:,}")
            st.metric("Est. Cost", f"${estimated_cost:.4f}")
        else:
            st.write("Start interview to track")
        st.link_button("View Balance", "https://console.anthropic.com/settings/billing", use_container_width=True)

    st.divider()

    if st.session_state.started and st.session_state.runner:
        state = st.session_state.runner.get_state()

        # ASSESSMENT LEVEL - Prominent display
        st.subheader("Assessment")
        current_level = state.get("current_level", 0)
        level_name = state.get("level_name", "NOT_ASSESSED")

        level_display = {
            0: ("Not Yet Assessed", "gray"),
            1: ("FAIL", "red"),
            2: ("WEAK", "orange"),
            3: ("GOOD (Not Enough)", "yellow"),
            4: ("CLEAR PASS", "green"),
            5: ("OUTSTANDING", "blue")
        }

        display_name, color = level_display.get(current_level, ("Unknown", "gray"))
        emoji = get_level_emoji(current_level)

        # Large level display
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}44);
            border-left: 4px solid {color};
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        ">
            <div style="font-size: 2em;">{emoji}</div>
            <div style="font-size: 1.2em; font-weight: bold;">Level {current_level}</div>
            <div style="font-size: 0.9em;">{display_name}</div>
        </div>
        """, unsafe_allow_html=True)

        # Status
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Phase", state.get("current_phase", "N/A"))
        with col2:
            candidate_msgs = [m for m in state.get("messages", []) if m["role"] == "candidate"]
            st.metric("Exchanges", len(candidate_msgs))

        # Flags
        red_flags = state.get("red_flags", [])
        green_flags = state.get("green_flags", [])

        if red_flags or green_flags:
            with st.expander("Performance Signals", expanded=True):
                if green_flags:
                    st.write("**✅ Strengths:**")
                    for flag in green_flags[-3:]:  # Show last 3
                        st.write(f"• {flag}")

                if red_flags:
                    st.write("**⚠️ Concerns:**")
                    for flag in red_flags[-3:]:
                        st.write(f"• {flag}")

        # Debug
        with st.expander("Debug", expanded=False):
            if state.get("last_evaluator_output"):
                st.json(state["last_evaluator_output"])

        st.divider()
        if st.button("Reset Interview", type="secondary", use_container_width=True):
            reset_interview()
            st.rerun()

# Main content
st.title("Case Interview")

if not st.session_state.started:
    st.markdown("""
    This AI conducts realistic case interviews and assesses candidates on a 5-level scale:

    | Level | Assessment | Meaning |
    |-------|------------|---------|
    | 1 | FAIL | Unstructured, superficial |
    | 2 | WEAK | Structure without insight |
    | 3 | GOOD (Not Enough) | Solid but non-distinctive |
    | 4 | CLEAR PASS | Strong, structured, commercial |
    | 5 | OUTSTANDING | Top-tier / Bain-level |

    **Note:** The system will NOT rescue weak candidates. If you can't structure, that's the assessment.
    """)

    st.divider()

    cases = get_available_cases()
    if not cases:
        st.error("No cases found.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_case = st.selectbox(
                "Select a case:",
                cases,
                format_func=lambda x: x.replace("_", " ").title(),
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("Start Interview", type="primary", use_container_width=True):
                state = initialize_interview_state(selected_case)
                st.session_state.runner = InterviewRunner(state)
                st.session_state.started = True
                opening = st.session_state.runner.start()
                st.session_state.messages = [{"role": "interviewer", "content": opening}]
                st.rerun()

else:
    runner = st.session_state.runner
    state = runner.get_state()

    if runner.is_complete():
        st.success("Interview Complete")

        # Final Assessment
        final_level = state.get("current_level", 0)
        level_name = state.get("level_name", "NOT_ASSESSED")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final Level", f"{final_level}/5")
        with col2:
            st.metric("Assessment", level_name)
        with col3:
            msgs = [m for m in state.get("messages", []) if m["role"] == "candidate"]
            st.metric("Exchanges", len(msgs))

        # Flags summary
        red_flags = state.get("red_flags", [])
        green_flags = state.get("green_flags", [])

        if green_flags:
            st.subheader("✅ Strengths Demonstrated")
            for flag in green_flags:
                st.write(f"• {flag}")

        if red_flags:
            st.subheader("⚠️ Areas of Concern")
            for flag in red_flags:
                st.write(f"• {flag}")

        # Verdict
        st.subheader("Verdict")
        if final_level >= 4:
            st.success("Would put in front of client with normal supervision")
        elif final_level == 3:
            st.warning("Maybe with significant coaching")
        else:
            st.error("Would not put in front of client")

        if st.button("Start New Interview", type="primary"):
            reset_interview()
            st.rerun()

    else:
        st.subheader(f"Case: {state['case_title']}")

        for msg in st.session_state.messages:
            if msg["role"] == "interviewer":
                with st.chat_message("assistant", avatar="👔"):
                    st.write(msg["content"])
            else:
                with st.chat_message("user", avatar="👤"):
                    st.write(msg["content"])

        if prompt := st.chat_input("Your response..."):
            st.session_state.messages.append({"role": "candidate", "content": prompt})

            with st.spinner("..."):
                response = runner.respond(prompt)

            st.session_state.messages.append({"role": "interviewer", "content": response})
            st.rerun()

st.divider()
st.caption("Adaptive Case Interview System | Powered by Claude")
