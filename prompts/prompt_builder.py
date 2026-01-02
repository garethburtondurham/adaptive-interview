"""
Prompt Builder for the Context Injection Architecture.

This module builds interviewer prompts by combining:
1. A universal methodology (the core interviewer "OS")
2. Heuristics from the InterviewSpec (the "script" that adapts behavior)
3. Context from the interview type (case, CV, technical problem)

The interviewer is a "Method Actor" - same core capabilities, different script.
"""

import json
from typing import Dict, Any, Optional, List

from state import InterviewState, has_spec, get_heuristics, get_context_packet, get_current_phase_config


# =============================================================================
# UNIVERSAL INTERVIEWER METHODOLOGY
# =============================================================================
# This is the "operating system" of the interviewer - consistent across all
# interview types. The heuristics from the spec ADAPT this, not replace it.

UNIVERSAL_METHODOLOGY = """
## CORE PRINCIPLES (Always Apply)

1. **Let the candidate drive.**
   Strong candidates take ownership. Weak candidates wait to be led.
   Your job is to observe which one they are, not to compensate for gaps.

2. **Be realistic, not scripted.**
   Respond to what is actually happening. If they are progressing well,
   stay out of the way. If they are confused, respond as a real interviewer would.

3. **Do not rescue.**
   If they fail to structure, miss a key driver, or pursue noise, note it.
   Probe it. Do not fix it for them.

4. **Maintain momentum without leading.**
   Do not allow long stalls or circular discussion. Use neutral prompts
   to move things forward, without suggesting a path or solution.

5. **Never signal performance through tone.**
   Your responses should be indistinguishable whether the candidate is
   doing well or poorly. No "good question" or "interesting approach."

---

## FOLLOWING EVALUATOR GUIDANCE

You receive guidance from the evaluator including:
- **Action**: DO_NOT_HELP, MINIMAL_HELP, LIGHT_HELP, CHALLENGE, or LET_SHINE
- **Specific guidance**: What to do or ask next
- **Data to share**: What facts you're approved to share (if any)

Follow the evaluator's guidance while maintaining natural conversation:

- **DO_NOT_HELP**: Ask neutral questions. Do not hint or help. Let them struggle.
- **MINIMAL_HELP**: One small nudge at most. Then observe.
- **LIGHT_HELP**: Help with execution only. Not with thinking or direction.
- **CHALLENGE**: Push them further. Add complexity. Make them defend their thinking.
- **LET_SHINE**: Get out of the way. Let them demonstrate excellence.

---

## RESPONSE FORMAT

Respond with JSON only:

```json
{{
    "spoken": "<your response to the candidate - brief, natural, no markdown>"
}}
```

Keep "spoken" to 1-3 sentences maximum. Be natural - like a colleague having a conversation.
"""


# =============================================================================
# SITUATION-SPECIFIC RESPONSE PATTERNS
# =============================================================================
# These provide guidance for common situations. Heuristics from the spec
# may override or supplement these.

RESPONSE_PATTERNS = """
## HOW TO RESPOND IN DIFFERENT SITUATIONS

**When they're working through the problem:**
- Let them finish without interruption
- Use NEUTRAL responses that don't signal quality
- NEVER say "solid," "good," or "interesting" in ways that reveal assessment

**When they ask for information:**
- Check if evaluator has approved data to share
- If approved: Provide the data warmly and plainly
- If not approved: Redirect appropriately based on your heuristics

**When they're analyzing:**
- Let them work without signaling whether they're on track
- Use neutral acknowledgments: "Okay" / "Got it" / "Keep going"
- NEVER say "good line of inquiry" or similar

**When they're wrong:**
- Don't immediately correct
- Probe neutrally: "Walk me through that" or "What's driving that view?"
- See if they self-correct

**When they're stuck:**
- First: Give them space, don't rush them
- Then: "What are you thinking?" or "Take your time"
- If still stuck: Apply your hint philosophy from heuristics

**When they ask for clarification:**
- Be helpful: "Sure" or "Let me clarify"
- Explain concepts briefly and clearly
- Keep explanations concise - just enough to unblock them
"""


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_interviewer_prompt(state: InterviewState) -> str:
    """
    Build the complete interviewer system prompt.

    If the state has an InterviewSpec, builds a heuristics-driven prompt.
    Otherwise, falls back to the legacy case-specific prompt.

    Args:
        state: Current interview state

    Returns:
        Complete system prompt for the interviewer
    """
    if has_spec(state):
        return _build_spec_driven_prompt(state)
    else:
        # Fall back to legacy prompt for backward compatibility
        from prompts.interviewer_prompt import get_interviewer_system_prompt
        case_data = _extract_legacy_case_data(state)
        return get_interviewer_system_prompt(case_data)


def _build_spec_driven_prompt(state: InterviewState) -> str:
    """Build a prompt driven by the InterviewSpec."""

    spec = state.get("interview_spec", {})
    heuristics = get_heuristics(state) or {}
    context_packet = get_context_packet(state) or {}
    phase_config = get_current_phase_config(state)

    # Build the prompt in sections
    sections = []

    # 1. Role and Persona
    sections.append(_build_persona_section(heuristics, spec))

    # 2. Context Materials (what the interviewer "sees")
    sections.append(_build_context_section(context_packet, state))

    # 3. Behavioral Heuristics
    sections.append(_build_heuristics_section(heuristics, phase_config))

    # 4. Universal Methodology (adapted by heuristics)
    sections.append(UNIVERSAL_METHODOLOGY)

    # 5. Response Patterns (may be overridden by heuristics)
    sections.append(_build_response_patterns_section(heuristics))

    # 6. Current Phase Guidance
    if phase_config:
        sections.append(_build_phase_section(phase_config))

    return "\n\n".join(sections)


def _build_persona_section(heuristics: Dict[str, Any], spec: Dict[str, Any]) -> str:
    """Build the persona/role section."""

    interview_type = spec.get("interview_type", "interview")
    title = spec.get("title", "Interview")
    tone = heuristics.get("tone", "Professional and warm.")
    persona = heuristics.get("persona_description", "You are an experienced interviewer.")

    return f"""# YOUR ROLE

**Interview Type:** {interview_type.replace("_", " ").title()}
**Title:** {title}

**Tone:** {tone}

{persona}

Remember: You are executing methodology, not assessing. The evaluator handles assessment."""


def _build_context_section(context_packet: Dict[str, Any], state: InterviewState) -> str:
    """Build the context/materials section based on packet type."""

    packet_type = context_packet.get("packet_type", "")

    if packet_type == "case_study":
        return _build_case_context(context_packet, state)
    elif packet_type == "cv_screen":
        return _build_cv_context(context_packet)
    elif packet_type == "technical_problem":
        return _build_technical_context(context_packet)
    else:
        # Fallback for legacy state
        return _build_legacy_context(state)


def _build_case_context(context_packet: Dict[str, Any], state: InterviewState) -> str:
    """Build context section for case interviews."""

    case_study = context_packet.get("case_study", {})
    case_prompt = case_study.get("case_prompt", state.get("opening", ""))
    facts = case_study.get("facts", state.get("facts", {}))
    facts_text = json.dumps(facts, indent=2)

    return f"""---

## THE CASE

**Opening (present this to start):**
{case_prompt}

**Facts (share ONLY what the evaluator approves):**
{facts_text}

---"""


def _build_cv_context(context_packet: Dict[str, Any]) -> str:
    """Build context section for first-round screening."""

    cv_screen = context_packet.get("cv_screen", {})
    role_title = cv_screen.get("role_title", "")
    job_description = cv_screen.get("job_description", "")
    candidate_cv = cv_screen.get("candidate_cv", "")

    # Parsed insights
    gaps = cv_screen.get("gaps_to_probe", [])
    claims = cv_screen.get("claims_to_validate", [])

    gaps_text = "\n".join(f"- {g}" for g in gaps) if gaps else "None identified"
    claims_text = "\n".join(f"- {c}" for c in claims) if claims else "None identified"

    return f"""---

## CANDIDATE MATERIALS

**Role:** {role_title}

**Job Description:**
{job_description}

**Candidate CV:**
{candidate_cv}

---

## PROBING TARGETS

**Gaps to explore** (JD requirements not clearly evidenced in CV):
{gaps_text}

**Claims to validate** (specific CV claims to probe for depth):
{claims_text}

---"""


def _build_technical_context(context_packet: Dict[str, Any]) -> str:
    """Build context section for technical interviews."""

    tech = context_packet.get("technical_problem", {})
    problem = tech.get("problem_statement", "")
    starter = tech.get("starter_code", "")
    complexity = tech.get("expected_complexity", "")
    hints = tech.get("available_hints", [])
    pitfalls = tech.get("common_pitfalls", [])

    hints_text = "\n".join(
        f"- Level {h.get('level', '?')}: {h.get('hint', '')} (Score impact: {h.get('score_impact', 'none')})"
        for h in hints
    ) if hints else "No hints defined"

    pitfalls_text = "\n".join(f"- {p}" for p in pitfalls) if pitfalls else "None"

    section = f"""---

## THE PROBLEM

**Problem Statement:**
{problem}
"""

    if starter:
        section += f"""
**Starter Code:**
```
{starter}
```
"""

    if complexity:
        section += f"""
**Expected Complexity:** {complexity}
"""

    section += f"""
**Available Hints (use based on hint philosophy):**
{hints_text}

**Common Pitfalls to Watch For:**
{pitfalls_text}

---"""

    return section


def _build_legacy_context(state: InterviewState) -> str:
    """Build context from legacy state fields."""

    opening = state.get("opening", "")
    facts = state.get("facts", {})
    facts_text = json.dumps(facts, indent=2)

    return f"""---

## THE CASE

**Opening:**
{opening}

**Facts (share ONLY what the evaluator approves):**
{facts_text}

---"""


def _build_heuristics_section(heuristics: Dict[str, Any], phase_config: Optional[Dict[str, Any]]) -> str:
    """Build the behavioral heuristics section."""

    # Get base heuristics
    primary_mode = heuristics.get("primary_mode", "")
    silence_tolerance = heuristics.get("silence_tolerance", "")
    hint_philosophy = heuristics.get("hint_philosophy", "")
    rescue_policy = heuristics.get("rescue_policy", "")
    pushback_style = heuristics.get("pushback_style", "")
    follow_up_depth = heuristics.get("follow_up_depth", "")
    data_revelation = heuristics.get("data_revelation", "")

    # Check for phase-specific overrides
    if phase_config:
        overrides = phase_config.get("heuristic_overrides", {})
        if "pushback_style" in overrides:
            pushback_style = overrides["pushback_style"]
        if "hint_philosophy" in overrides:
            hint_philosophy = overrides["hint_philosophy"]
        if "data_revelation" in overrides:
            data_revelation = overrides["data_revelation"]
        if "primary_mode" in overrides:
            primary_mode = overrides["primary_mode"]

    return f"""---

## YOUR BEHAVIORAL HEURISTICS

**Primary Mode:** {primary_mode}

**Silence Tolerance:** {silence_tolerance}

**Hint Philosophy:** {hint_philosophy}

**Rescue Policy:** {rescue_policy}

**Pushback Style:** {pushback_style}

**Follow-up Depth:** {follow_up_depth}

**Data/Information Revelation:** {data_revelation}

---"""


def _build_response_patterns_section(heuristics: Dict[str, Any]) -> str:
    """Build response patterns, incorporating heuristics."""

    # Start with universal patterns
    patterns = RESPONSE_PATTERNS

    # Add heuristics-specific guidance
    opening_style = heuristics.get("opening_style", "")
    closing_style = heuristics.get("closing_style", "")

    if opening_style or closing_style:
        patterns += f"""
---

## OPENING AND CLOSING

**Opening Style:** {opening_style}

**Closing Style:** {closing_style}
"""

    return patterns


def _build_phase_section(phase_config: Dict[str, Any]) -> str:
    """Build current phase guidance."""

    phase_name = phase_config.get("name", "")
    phase_objective = phase_config.get("objective", "")
    focus_competencies = phase_config.get("focus_competencies", [])
    transition_signals = phase_config.get("transition_signals", [])

    focus_text = ", ".join(focus_competencies) if focus_competencies else "All competencies"
    signals_text = "\n".join(f"- {s}" for s in transition_signals) if transition_signals else "None specific"

    return f"""---

## CURRENT PHASE: {phase_name}

**Objective:** {phase_objective}

**Competencies to Focus On:** {focus_text}

**Signals This Phase May Be Complete:**
{signals_text}

Note: Phase transitions are fluid. The Manager will suggest when to transition.
Continue naturally - don't force transitions.

---"""


def _extract_legacy_case_data(state: InterviewState) -> Dict[str, Any]:
    """Extract case data from legacy state fields."""
    return {
        "opening": state.get("opening", ""),
        "facts": state.get("facts", {}),
        "root_cause": state.get("root_cause", ""),
        "strong_recommendations": state.get("strong_recommendations", []),
        "calibration": state.get("calibration", {}),
        "red_flags": state.get("case_red_flags", []),
        "green_flags": state.get("case_green_flags", [])
    }


# =============================================================================
# OPENING MESSAGE BUILDERS
# =============================================================================

def build_opening_message(state: InterviewState) -> str:
    """
    Build the opening message for the interview.

    This is the first thing the candidate sees/hears.
    """
    if has_spec(state):
        return _build_spec_opening(state)
    else:
        # Legacy: return the case opening directly
        return state.get("opening", "")


def _build_spec_opening(state: InterviewState) -> str:
    """Build opening from spec context."""

    context_packet = get_context_packet(state) or {}
    packet_type = context_packet.get("packet_type", "")
    heuristics = get_heuristics(state) or {}

    if packet_type == "case_study":
        case_study = context_packet.get("case_study", {})
        return case_study.get("case_prompt", state.get("opening", ""))

    elif packet_type == "cv_screen":
        cv_screen = context_packet.get("cv_screen", {})
        role = cv_screen.get("role_title", "the role")
        # First round opens conversationally
        opening_style = heuristics.get("opening_style", "")
        return f"Thanks for joining me today. I'm excited to learn more about your background and discuss the {role} position. {opening_style}"

    elif packet_type == "technical_problem":
        tech = context_packet.get("technical_problem", {})
        return tech.get("problem_statement", "")

    else:
        return state.get("opening", "")


# =============================================================================
# COMPETENCY CONTEXT FOR EVALUATOR
# =============================================================================

def build_competency_context(state: InterviewState) -> str:
    """
    Build context about competencies being assessed.

    Used by the evaluator to understand what to look for.
    """
    if not has_spec(state):
        return ""

    spec = state.get("interview_spec", {})
    competencies = spec.get("competencies", [])

    if not competencies:
        return ""

    # Import the universal rubric to get full definitions
    try:
        from specs.spec_schema import UNIVERSAL_RUBRIC
    except ImportError:
        return ""

    sections = ["## COMPETENCIES BEING ASSESSED\n"]

    for comp in competencies:
        comp_id = comp.get("competency_id", "")
        tier = comp.get("tier", "important")

        full_comp = UNIVERSAL_RUBRIC.get(comp_id)
        if not full_comp:
            continue

        tier_label = {
            "critical": "CRITICAL (must pass)",
            "important": "Important",
            "bonus": "Bonus"
        }.get(tier, tier)

        sections.append(f"### {full_comp.name} [{tier_label}]")
        sections.append(f"{full_comp.description}\n")

        # Add level indicators
        sections.append("**Levels:**")
        for level_num in [5, 4, 3, 2, 1]:
            level = full_comp.levels.get(level_num)
            if level:
                sections.append(f"- Level {level_num} ({level.name}): {level.description}")

        # Add flags
        all_red = list(full_comp.red_flags) + comp.get("additional_red_flags", [])
        all_green = list(full_comp.green_flags) + comp.get("additional_green_flags", [])

        if all_red:
            sections.append(f"\n**Red Flags:** {', '.join(all_red[:3])}")
        if all_green:
            sections.append(f"**Green Flags:** {', '.join(all_green[:3])}")

        sections.append("")  # Blank line between competencies

    return "\n".join(sections)
