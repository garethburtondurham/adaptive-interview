"""
Streamlit Web Interface for the Adaptive Interview System.

Supports multiple interview types:
- First-round screening (from JD/CV) - PRIMARY
- Case interviews (from case files)
- Technical interviews (from problem files)

Run with: streamlit run ui/reviewer_dashboard.py
"""
import sys
from pathlib import Path
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import streamlit as st
from case_loader import initialize_interview_state, get_available_cases
from graph import InterviewRunner
from interview_factory import (
    create_case_interview,
    create_first_round_interview,
    create_first_round_interview_simple,
    create_technical_interview,
    list_available_cases,
)


def extract_text_from_file(uploaded_file) -> str:
    """Legacy wrapper - use extract_text_from_bytes instead."""
    if uploaded_file is None:
        return ""
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    return extract_text_from_bytes(file_bytes, uploaded_file.name)


def extract_text_from_bytes(file_bytes: bytes, file_name: str) -> str:
    """
    Extract text content from file bytes.

    Supports: PDF, DOCX, TXT, MD
    """
    if not file_bytes:
        return ""

    file_name_lower = file_name.lower()

    try:
        # Plain text files
        if file_name_lower.endswith(('.txt', '.md')):
            return file_bytes.decode('utf-8')

        # PDF files
        elif file_name_lower.endswith('.pdf'):
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                text_parts = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                result = "\n".join(text_parts)
                if not result.strip():
                    st.warning("PDF appears to be empty or image-based. Text extraction may not work.")
                return result
            except ImportError:
                st.error("PyPDF2 not installed. Run: pip install PyPDF2")
                return ""
            except Exception as e:
                st.error(f"PDF extraction error: {str(e)}")
                return ""

        # Word documents
        elif file_name_lower.endswith('.docx'):
            try:
                from docx import Document
                doc = Document(io.BytesIO(file_bytes))
                text_parts = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)
                return "\n".join(text_parts)
            except ImportError:
                st.error("python-docx not installed. Run: pip install python-docx")
                return ""
            except Exception as e:
                st.error(f"DOCX extraction error: {str(e)}")
                return ""

        else:
            st.warning(f"Unsupported file type: {file_name}. Supported: PDF, DOCX, TXT, MD")
            return ""

    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""


def summarize_with_ai(text: str, doc_type: str) -> str:
    """
    Use AI to summarize a document into a concise format.

    Args:
        text: The raw document text
        doc_type: Either "jd" (job description) or "cv" (resume)

    Returns:
        Summarized text
    """
    if not text.strip():
        return ""

    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.1,
        max_tokens=1500,
    )

    if doc_type == "jd":
        system_prompt = """You are an expert at extracting key information from job descriptions.

Summarize this job description into a clear, structured format:

1. Role Title & Level
2. Key Requirements (must-haves)
3. Nice-to-haves
4. Key Responsibilities
5. Any specific skills or experience mentioned

Be concise but capture all important details that an interviewer would need."""
    else:  # cv
        system_prompt = """You are an expert at extracting key information from CVs/resumes.

Summarize this CV into a clear, structured format:

1. Candidate Profile (name, current role)
2. Years of Experience
3. Key Skills & Technologies
4. Career Progression (most recent roles)
5. Notable Achievements (quantified if possible)
6. Education

Be concise but capture all important details that an interviewer would need to assess this candidate."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Document to summarize:\n\n{text[:8000]}")  # Limit to 8k chars
        ]
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        st.error(f"AI summarization failed: {str(e)}")
        return text  # Return original text on failure


st.set_page_config(
    page_title="Interview System",
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
if "interview_type" not in st.session_state:
    st.session_state.interview_type = None


def reset_interview():
    st.session_state.runner = None
    st.session_state.started = False
    st.session_state.messages = []
    st.session_state.interview_type = None


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
        0: "?",
        1: "X",
        2: "!",
        3: "~",
        4: "+",
        5: "*"
    }
    return emojis.get(level, "?")


def render_competency_scores(state):
    """Render the multi-competency scoring panel."""
    competency_scores = state.get("competency_scores", {})
    spec = state.get("interview_spec", {})

    if not competency_scores:
        return

    # Get competency tiers
    competency_tiers = {}
    competency_names = {}
    for comp in spec.get("competencies", []):
        comp_id = comp.get("competency_id", comp.get("id"))
        competency_tiers[comp_id] = comp.get("tier", "important")
        competency_names[comp_id] = comp_id.replace("_", " ").title()

    st.subheader("Competency Scores")

    # Group by tier
    critical_scores = []
    important_scores = []
    bonus_scores = []

    for comp_id, score in competency_scores.items():
        tier = competency_tiers.get(comp_id, "important")
        level = score.get("current_level", 0)
        confidence = score.get("confidence", "low")
        name = competency_names.get(comp_id, comp_id)

        entry = {"id": comp_id, "name": name, "level": level, "confidence": confidence}

        if tier == "critical":
            critical_scores.append(entry)
        elif tier == "important":
            important_scores.append(entry)
        else:
            bonus_scores.append(entry)

    # Render critical competencies
    if critical_scores:
        st.markdown("**CRITICAL** (must pass)")
        for entry in critical_scores:
            level = entry["level"]
            color = "red" if level < 3 and level > 0 else ("green" if level >= 3 else "gray")
            emoji = get_level_emoji(level)
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                padding: 4px 8px;
                background: {color}22;
                border-left: 3px solid {color};
                margin-bottom: 4px;
                border-radius: 4px;
            ">
                <span>{entry['name']}</span>
                <span>{emoji} {level}/5</span>
            </div>
            """, unsafe_allow_html=True)

    # Render important competencies
    if important_scores:
        st.markdown("**IMPORTANT**")
        for entry in important_scores:
            level = entry["level"]
            color = get_level_color(level)
            emoji = get_level_emoji(level)
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                padding: 4px 8px;
                background: {color}22;
                border-left: 3px solid {color};
                margin-bottom: 4px;
                border-radius: 4px;
            ">
                <span>{entry['name']}</span>
                <span>{emoji} {level}/5</span>
            </div>
            """, unsafe_allow_html=True)

    # Render bonus competencies
    if bonus_scores:
        st.markdown("**BONUS**")
        for entry in bonus_scores:
            level = entry["level"]
            color = get_level_color(level) if level > 0 else "gray"
            emoji = get_level_emoji(level)
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                padding: 4px 8px;
                background: {color}11;
                border-left: 2px solid {color};
                margin-bottom: 4px;
                border-radius: 4px;
                font-size: 0.9em;
            ">
                <span>{entry['name']}</span>
                <span>{emoji} {level}/5</span>
            </div>
            """, unsafe_allow_html=True)


def render_manager_directive(state):
    """Render the manager directive panel."""
    directive = state.get("manager_directive")
    if not directive:
        return

    urgency = directive.get("urgency", "normal")
    focus = directive.get("focus_area", "")
    undercovered = directive.get("undercovered_competencies", [])
    suggested_phase = directive.get("suggested_phase", "")

    urgency_colors = {
        "normal": "green",
        "wrap_up_soon": "orange",
        "must_end": "red"
    }
    color = urgency_colors.get(urgency, "gray")

    with st.expander("Manager Directive", expanded=False):
        st.markdown(f"**Urgency:** :{color}[{urgency}]")

        if focus:
            st.markdown(f"**Focus:** {focus}")

        if undercovered:
            st.markdown("**Need more signal:**")
            for comp in undercovered:
                st.markdown(f"- {comp.replace('_', ' ').title()}")

        if suggested_phase:
            reason = directive.get("phase_suggestion_reason", "")
            st.markdown(f"**Suggested phase:** {suggested_phase}")
            if reason:
                st.caption(reason)


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

        # Show interview type
        interview_type = st.session_state.interview_type or "case"
        type_labels = {
            "case": "Case Interview",
            "first_round": "First Round",
            "technical": "Technical"
        }
        st.caption(f"Type: {type_labels.get(interview_type, interview_type)}")

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

        # Competency scores (if using spec system)
        if state.get("interview_spec"):
            render_competency_scores(state)
            render_manager_directive(state)

        # Evaluator Guidance
        evaluator_action = state.get("evaluator_action", "")
        evaluator_guidance = state.get("evaluator_guidance", "")
        if evaluator_action:
            with st.expander("Evaluator", expanded=True):
                st.code(evaluator_action, language=None)
                if evaluator_guidance:
                    guidance_text = evaluator_guidance[:120] + "..." if len(evaluator_guidance) > 120 else evaluator_guidance
                    st.caption(guidance_text)

        # Flags
        red_flags = state.get("red_flags_observed", [])
        green_flags = state.get("green_flags_observed", [])

        if red_flags or green_flags:
            with st.expander("Signals", expanded=True):
                if green_flags:
                    for flag in green_flags[-2:]:
                        flag_text = flag[:60] + "..." if len(flag) > 60 else flag
                        st.success(flag_text)

                if red_flags:
                    for flag in red_flags[-2:]:
                        flag_text = flag[:60] + "..." if len(flag) > 60 else flag
                        st.error(flag_text)

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
st.title("Interview System")

if not st.session_state.started:
    # Interview Type Selection
    st.markdown("""
    Select an interview type and configure the session.
    """)

    interview_type = st.radio(
        "Interview Type",
        ["First Round Screening", "Case Interview", "Technical Interview"],
        horizontal=True,
        key="interview_type_selector"
    )

    st.divider()

    # ==========================================================================
    # FIRST ROUND SCREENING SETUP (Now first!)
    # ==========================================================================
    if interview_type == "First Round Screening":
        st.markdown("""
        **First Round Screening** - Validate experience, probe gaps, assess fit.

        Competencies assessed:
        - **Experience Depth** (CRITICAL) - Can they back up their claims with specifics?
        - **Communication** (CRITICAL) - Do they articulate clearly?
        - **Self-Awareness** - Honest about limitations?
        - **Role Motivation** - Why this role, this company?
        """)

        st.divider()

        # Role Title
        role_title = st.text_input(
            "Role Title",
            placeholder="e.g., Senior Product Manager",
            help="The title of the position being interviewed for"
        )

        # Company Context
        company_context = st.text_input(
            "Company Context (Optional)",
            placeholder="e.g., B2B SaaS, Series B startup",
            help="Brief context about the company"
        )

        st.markdown("---")

        # Initialize session state
        if "jd_text" not in st.session_state:
            st.session_state.jd_text = ""
        if "cv_text" not in st.session_state:
            st.session_state.cv_text = ""

        # Two columns for JD and CV
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Job Description**")

            # File uploader for JD
            jd_file = st.file_uploader(
                "Upload JD (PDF, DOCX, TXT)",
                type=['pdf', 'docx', 'txt', 'md'],
                key="jd_uploader",
                help="Upload a job description file"
            )

            # Process uploaded file immediately
            if jd_file is not None:
                file_id = f"{jd_file.name}_{jd_file.size}"
                if st.session_state.get("_jd_file_id") != file_id:
                    jd_file.seek(0)
                    file_bytes = jd_file.read()
                    jd_file.seek(0)  # Reset for potential re-read
                    extracted = extract_text_from_bytes(file_bytes, jd_file.name)
                    if extracted:
                        st.session_state.jd_text = extracted
                        st.session_state.jd_input = extracted  # Update widget key
                        st.session_state._jd_file_id = file_id
                        st.rerun()

            # AI Summarize button for JD
            if st.button("AI Summarize JD", key="summarize_jd"):
                # Get current text from either session state
                current_jd_text = st.session_state.get("jd_input") or st.session_state.jd_text
                if current_jd_text:
                    with st.spinner("Summarizing job description..."):
                        summarized = summarize_with_ai(current_jd_text, "jd")
                        if summarized:
                            st.session_state.jd_text = summarized
                            # Also update the widget's key to force refresh
                            st.session_state.jd_input = summarized
                            st.rerun()
                else:
                    st.warning("Please upload or paste a job description first")

            # Text area for JD - using session state directly
            job_description = st.text_area(
                "Job Description Text",
                value=st.session_state.jd_text,
                height=200,
                placeholder="Paste the full job description here or upload a file above...",
                key="jd_input"
            )
            if job_description != st.session_state.jd_text:
                st.session_state.jd_text = job_description

        with col2:
            st.markdown("**Candidate CV/Resume**")

            # File uploader for CV
            cv_file = st.file_uploader(
                "Upload CV (PDF, DOCX, TXT)",
                type=['pdf', 'docx', 'txt', 'md'],
                key="cv_uploader",
                help="Upload a candidate CV/resume file"
            )

            # Process uploaded file immediately
            if cv_file is not None:
                file_id = f"{cv_file.name}_{cv_file.size}"
                if st.session_state.get("_cv_file_id") != file_id:
                    cv_file.seek(0)
                    file_bytes = cv_file.read()
                    cv_file.seek(0)  # Reset for potential re-read
                    extracted = extract_text_from_bytes(file_bytes, cv_file.name)
                    if extracted:
                        st.session_state.cv_text = extracted
                        st.session_state.cv_input = extracted  # Update widget key
                        st.session_state._cv_file_id = file_id
                        st.rerun()

            # AI Summarize button for CV
            if st.button("AI Summarize CV", key="summarize_cv"):
                # Get current text from either session state
                current_cv_text = st.session_state.get("cv_input") or st.session_state.cv_text
                if current_cv_text:
                    with st.spinner("Summarizing CV..."):
                        summarized = summarize_with_ai(current_cv_text, "cv")
                        if summarized:
                            st.session_state.cv_text = summarized
                            # Also update the widget's key to force refresh
                            st.session_state.cv_input = summarized
                            st.rerun()
                else:
                    st.warning("Please upload or paste a CV first")

            # Text area for CV - using session state directly
            candidate_cv = st.text_area(
                "CV/Resume Text",
                value=st.session_state.cv_text,
                height=200,
                placeholder="Paste the candidate's CV or resume here or upload a file above...",
                key="cv_input"
            )
            if candidate_cv != st.session_state.cv_text:
                st.session_state.cv_text = candidate_cv

        st.markdown("---")

        if st.button("Start First Round Interview", type="primary"):
            if not role_title or not job_description or not candidate_cv:
                st.error("Please fill in Role Title, Job Description, and Candidate CV.")
            else:
                with st.spinner("Preparing interview (analyzing JD/CV for gaps)..."):
                    runner = create_first_round_interview(
                        job_description=job_description,
                        candidate_cv=candidate_cv,
                        role_title=role_title,
                        company_context=company_context if company_context else None,
                        use_llm_parsing=True,  # Always analyze
                    )
                    st.session_state.runner = runner
                    st.session_state.started = True
                    st.session_state.interview_type = "first_round"
                    opening = runner.start()
                    st.session_state.messages = [{"role": "interviewer", "content": opening}]
                    # Clear the uploaded file text from session state
                    st.session_state.jd_text = ""
                    st.session_state.cv_text = ""
                st.rerun()

    # ==========================================================================
    # CASE INTERVIEW SETUP
    # ==========================================================================
    elif interview_type == "Case Interview":
        st.markdown("""
        **Case Interview** - Assess problem-solving, structuring, and analytical skills.

        | Level | Assessment | Meaning |
        |-------|------------|---------|
        | 1 | FAIL | Unstructured, superficial |
        | 2 | WEAK | Structure without insight |
        | 3 | GOOD (Not Enough) | Solid but non-distinctive |
        | 4 | CLEAR PASS | Strong, structured, commercial |
        | 5 | OUTSTANDING | Top-tier |

        **Note:** The system will NOT rescue weak candidates.
        """)

        st.divider()

        cases = get_available_cases()
        if not cases:
            st.error("No cases found in the cases/ directory.")
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
                if st.button("Start Case Interview", type="primary", use_container_width=True):
                    # Use legacy flow for now (backward compatible)
                    state = initialize_interview_state(selected_case)
                    st.session_state.runner = InterviewRunner(state)
                    st.session_state.started = True
                    st.session_state.interview_type = "case"
                    opening = st.session_state.runner.start()
                    st.session_state.messages = [{"role": "interviewer", "content": opening}]
                    st.rerun()

    # ==========================================================================
    # TECHNICAL INTERVIEW SETUP
    # ==========================================================================
    elif interview_type == "Technical Interview":
        st.markdown("""
        **Technical Interview** - Assess coding, problem-solving, and technical communication.

        Competencies assessed:
        - **Problem Decomposition** (CRITICAL) - Break down the problem?
        - **Code Quality** (CRITICAL) - Clean, correct, efficient code?
        - **Technical Communication** (CRITICAL) - Explain their thinking?
        - **Testing Mindset** - Think about edge cases?
        - **Complexity Optimization** - Consider time/space tradeoffs?
        """)

        st.divider()

        st.info("Technical interview requires a problem definition. Enter the problem details below:")

        problem_title = st.text_input(
            "Problem Title",
            placeholder="e.g., Two Sum"
        )

        problem_statement = st.text_area(
            "Problem Statement",
            height=150,
            placeholder="Describe the coding problem clearly..."
        )

        col1, col2 = st.columns(2)
        with col1:
            expected_complexity = st.text_input(
                "Expected Complexity",
                placeholder="e.g., O(n)"
            )

        with col2:
            language = st.selectbox(
                "Primary Language",
                ["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Any"]
            )

        starter_code = st.text_area(
            "Starter Code (Optional)",
            height=100,
            placeholder="def two_sum(nums, target):\n    # Your code here\n    pass"
        )

        hints = st.text_area(
            "Available Hints (one per line)",
            height=80,
            placeholder="Consider using a hash map\nThink about the time complexity"
        )

        if st.button("Start Technical Interview", type="primary"):
            if not problem_statement:
                st.error("Please provide a problem statement.")
            else:
                problem_data = {
                    "title": problem_title or "Coding Problem",
                    "problem_statement": problem_statement,
                    "expected_complexity": expected_complexity,
                    "starter_code": starter_code if starter_code else None,
                    "hints": [h.strip() for h in hints.split("\n") if h.strip()] if hints else [],
                    "language": language,
                }

                with st.spinner("Preparing interview..."):
                    runner = create_technical_interview(problem_data)
                    st.session_state.runner = runner
                    st.session_state.started = True
                    st.session_state.interview_type = "technical"
                    opening = runner.start()
                    st.session_state.messages = [{"role": "interviewer", "content": opening}]
                st.rerun()

else:
    # ==========================================================================
    # ACTIVE INTERVIEW SESSION
    # ==========================================================================
    runner = st.session_state.runner
    state = runner.get_state()
    interview_type = st.session_state.interview_type

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

        # Competency breakdown (if using spec)
        if state.get("interview_spec"):
            st.subheader("Competency Breakdown")
            render_competency_scores(state)

        # Flags summary
        red_flags = state.get("red_flags_observed", [])
        green_flags = state.get("green_flags_observed", [])

        if green_flags:
            st.subheader("Strengths Demonstrated")
            for flag in green_flags:
                st.write(f"+ {flag}")

        if red_flags:
            st.subheader("Areas of Concern")
            for flag in red_flags:
                st.write(f"- {flag}")

        # Verdict
        st.subheader("Verdict")
        if final_level >= 4:
            st.success("Strong candidate - recommend proceeding")
        elif final_level == 3:
            st.warning("Borderline - may need additional evaluation")
        else:
            st.error("Below bar - do not proceed")

        if st.button("Start New Interview", type="primary"):
            reset_interview()
            st.rerun()

    else:
        # Display the opening/context prominently
        if st.session_state.messages:
            first_msg = st.session_state.messages[0]
            if first_msg["role"] == "interviewer":
                content = first_msg["content"]

                # Get title based on interview type
                if interview_type == "case":
                    title_prefix = f"CASE: {state.get('case_title', 'Case Interview')}"
                elif interview_type == "first_round":
                    spec = state.get("interview_spec", {})
                    title_prefix = f"FIRST ROUND: {spec.get('title', 'Screening Interview')}"
                elif interview_type == "technical":
                    spec = state.get("interview_spec", {})
                    title_prefix = f"TECHNICAL: {spec.get('title', 'Coding Interview')}"
                else:
                    title_prefix = "INTERVIEW"

                # For case interviews, try to split question from guidelines
                if interview_type == "case" and "Take a moment" in content:
                    parts = content.split("Take a moment")
                    case_question = parts[0].strip()
                    guidelines = "Take a moment" + parts[1] if len(parts) > 1 else ""
                else:
                    case_question = content
                    guidelines = ""

                # Question/Context Box
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
                    ">{title_prefix}</div>
                    <div style="
                        color: #eee;
                        font-size: 1em;
                        line-height: 1.6;
                        white-space: pre-wrap;
                    ">{case_question}</div>
                </div>
                """, unsafe_allow_html=True)

                # Guidelines Box (for case interviews)
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
                with st.chat_message("assistant"):
                    st.write(msg["content"])
            else:
                with st.chat_message("user"):
                    st.write(msg["content"])

        if prompt := st.chat_input("Your response..."):
            st.session_state.messages.append({"role": "candidate", "content": prompt})

            with st.spinner("..."):
                response = runner.respond(prompt)

            st.session_state.messages.append({"role": "interviewer", "content": response})
            st.rerun()

st.divider()
st.caption("Adaptive Interview System | Powered by Claude")
