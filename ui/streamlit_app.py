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

        # Evaluator Guidance
        evaluator_action = state.get("evaluator_action", "")
        evaluator_guidance = state.get("evaluator_guidance", "")
        if evaluator_action:
            with st.expander("Evaluator", expanded=True):
                st.code(evaluator_action, language=None)
                if evaluator_guidance:
                    # Truncate and use a scrollable container
                    guidance_text = evaluator_guidance[:120] + "..." if len(evaluator_guidance) > 120 else evaluator_guidance
                    st.caption(guidance_text)

        # Flags
        red_flags = state.get("red_flags_observed", [])
        green_flags = state.get("green_flags_observed", [])

        if red_flags or green_flags:
            with st.expander("Signals", expanded=True):
                if green_flags:
                    for flag in green_flags[-2:]:  # Show last 2 only
                        flag_text = flag[:60] + "..." if len(flag) > 60 else flag
                        st.success(flag_text, icon="✅")

                if red_flags:
                    for flag in red_flags[-2:]:  # Show last 2 only
                        flag_text = flag[:60] + "..." if len(flag) > 60 else flag
                        st.error(flag_text, icon="⚠️")

        # Debug
        with st.expander("Debug", expanded=False):
            st.write("**Level History:**")
            level_history = state.get("level_history", [])
            if level_history:
                for entry in level_history[-3:]:
                    st.write(f"Level {entry.get('level')}: {entry.get('justification', '')[:100]}...")

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
        red_flags = state.get("red_flags_observed", [])
        green_flags = state.get("green_flags_observed", [])

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
        # Display the case question prominently at the top (separate from guidelines)
        if st.session_state.messages:
            first_msg = st.session_state.messages[0]
            if first_msg["role"] == "interviewer":
                # Split case question from guidelines
                content = first_msg["content"]
                # The guidelines start with "Take a moment..."
                if "Take a moment" in content:
                    parts = content.split("Take a moment")
                    case_question = parts[0].strip()
                    guidelines = "Take a moment" + parts[1] if len(parts) > 1 else ""
                else:
                    case_question = content
                    guidelines = ""

                # Case Question Box
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1a1a2e, #16213e);
                    border: 2px solid #0f3460;
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 16px;
                ">
                    <div style="
                        color: #e94560;
                        font-size: 0.85em;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-bottom: 12px;
                    ">CASE QUESTION — {state['case_title']}</div>
                    <div style="
                        color: #eee;
                        font-size: 1em;
                        line-height: 1.6;
                        white-space: pre-wrap;
                    ">{case_question}</div>
                </div>
                """, unsafe_allow_html=True)

                # Guidelines Box (separate, lighter style)
                if guidelines:
                    st.markdown(f"""
                    <div style="
                        background: #2a2a3a;
                        border-left: 3px solid #888;
                        border-radius: 4px;
                        padding: 16px;
                        margin-bottom: 24px;
                        font-size: 0.9em;
                        color: #bbb;
                    ">
                        <div style="
                            font-weight: 600;
                            margin-bottom: 8px;
                            color: #999;
                        ">INTERVIEWER</div>
                        {guidelines}
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Dialogue**")

        # Show conversation (skip first message as it's displayed above)
        for msg in st.session_state.messages[1:]:
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
