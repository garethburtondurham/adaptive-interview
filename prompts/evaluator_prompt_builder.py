"""
Evaluator Prompt Builder for the Context Injection Architecture.

This module builds evaluator prompts that assess candidates against
the competencies defined in the InterviewSpec.

The evaluator:
- Scores each competency independently (multi-dimensional assessment)
- Provides action guidance for the interviewer
- Approves data sharing based on interview type rules
"""

import json
from typing import Dict, Any, List, Optional

from state import InterviewState, has_spec, get_heuristics, get_context_packet


def build_evaluator_prompt(state: InterviewState) -> str:
    """
    Build the complete evaluator system prompt.

    If the state has an InterviewSpec, builds a competency-driven prompt.
    Otherwise, falls back to the legacy evaluator prompt.

    Args:
        state: Current interview state

    Returns:
        Complete system prompt for the evaluator
    """
    if has_spec(state):
        return _build_spec_driven_evaluator_prompt(state)
    else:
        # Fall back to legacy prompt
        from prompts.evaluator_prompt import get_evaluator_system_prompt
        from case_loader import get_case_data
        case_data = get_case_data(state)
        return get_evaluator_system_prompt(case_data)


def _build_spec_driven_evaluator_prompt(state: InterviewState) -> str:
    """Build an evaluator prompt driven by the InterviewSpec."""

    spec = state.get("interview_spec", {})
    heuristics = get_heuristics(state) or {}
    context_packet = get_context_packet(state) or {}

    # Build sections
    sections = []

    # 1. Role and Purpose
    sections.append(_build_evaluator_role_section(spec))

    # 2. Context for Evaluation
    sections.append(_build_evaluation_context_section(context_packet, state))

    # 3. Competencies to Assess
    sections.append(_build_competencies_section(spec))

    # 4. Level Definitions (universal)
    sections.append(_build_level_definitions_section())

    # 5. Action Mapping
    sections.append(_build_action_mapping_section(heuristics, spec))

    # 6. Data Approval Rules (adapted by interview type)
    sections.append(_build_data_approval_section(spec, heuristics))

    # 7. Output Format
    sections.append(_build_output_format_section(spec))

    # 8. Critical Rules
    sections.append(_build_critical_rules_section(heuristics, spec))

    return "\n\n".join(sections)


def _build_evaluator_role_section(spec: Dict[str, Any]) -> str:
    """Build the evaluator's role description."""

    interview_type = spec.get("interview_type", "interview")
    title = spec.get("title", "Interview")

    return f"""# YOUR ROLE: Assessment Authority

You are the assessment authority for this {interview_type.replace("_", " ")} interview.
**Interview:** {title}

Your job is to:
1. Assess the candidate's performance on EACH competency (1-5 scale)
2. Decide what action the interviewer should take
3. Provide specific guidance for the interviewer's next response
4. Approve what data/information can be shared with the candidate

You do NOT interact with the candidate directly. You provide guidance to the interviewer."""


def _build_evaluation_context_section(context_packet: Dict[str, Any], state: InterviewState) -> str:
    """Build context about what's being evaluated."""

    packet_type = context_packet.get("packet_type", "")

    if packet_type == "case_study":
        return _build_case_evaluation_context(context_packet, state)
    elif packet_type == "cv_screen":
        return _build_cv_evaluation_context(context_packet)
    elif packet_type == "technical_problem":
        return _build_technical_evaluation_context(context_packet)
    else:
        return _build_legacy_evaluation_context(state)


def _build_case_evaluation_context(context_packet: Dict[str, Any], state: InterviewState) -> str:
    """Build evaluation context for case interviews."""

    case_study = context_packet.get("case_study", {})
    root_cause = case_study.get("root_cause", state.get("root_cause", ""))
    strong_recs = case_study.get("strong_recommendations", state.get("strong_recommendations", []))
    facts = case_study.get("facts", state.get("facts", {}))

    recs_text = "\n".join(f"- {r}" for r in strong_recs[:3]) if strong_recs else "Not specified"
    facts_text = json.dumps(facts, indent=2)

    # Get calibration examples if available
    calibration = case_study.get("calibration_examples", state.get("calibration", {}))
    calibration_text = _format_calibration_examples(calibration)

    return f"""---

## EVALUATION CONTEXT: Case Interview

**What Good Looks Like (Root Cause):**
{root_cause}

**Strong Recommendations Include:**
{recs_text}

**Available Facts (approve for sharing when earned):**
{facts_text}

{calibration_text}

---"""


def _build_cv_evaluation_context(context_packet: Dict[str, Any]) -> str:
    """Build evaluation context for first-round screening."""

    cv_screen = context_packet.get("cv_screen", {})
    role_title = cv_screen.get("role_title", "")
    gaps = cv_screen.get("gaps_to_probe", [])
    claims = cv_screen.get("claims_to_validate", [])

    gaps_text = "\n".join(f"- {g}" for g in gaps) if gaps else "None identified"
    claims_text = "\n".join(f"- {c}" for c in claims) if claims else "None identified"

    return f"""---

## EVALUATION CONTEXT: First Round Screening

**Role:** {role_title}

**Areas to Explore** (JD requirements not evidenced in CV):
{gaps_text}

**Topics to Understand** (CV claims worth exploring):
{claims_text}

## FIRST ROUND PHILOSOPHY

This is a **smart exploration via conversation**, NOT an interrogation.

**Test Understanding Conceptually, Not Numbers:**
- When a candidate mentions a topic (e.g., "card not present rates"), explore their UNDERSTANDING of it
- Don't demand exact figures they wouldn't know off-hand
- Ask: "What made you look at that?" "How did you think about it?" "What trade-offs did you consider?"

**Find the Natural Edge of Understanding:**
- Move SLOWLY through topics they raise
- Follow the thread of their thinking with curiosity
- When their answers become vague or they acknowledge uncertainty, you've found their limit
- That's the signal you need - then move on gracefully to the next topic

**What to Assess:**
- Do they understand the CONCEPTS behind what they did?
- Can they explain their reasoning and trade-offs?
- Where does their genuine understanding taper off?
- Is there depth of thinking, not just surface exposure?

**What NOT to Do:**
- Don't push for exact numbers/metrics from years ago
- Don't cross-examine or make them feel pressured
- Don't treat this like a case interview with right/wrong answers
- Don't rush - this is exploratory conversation

---"""


def _build_technical_evaluation_context(context_packet: Dict[str, Any]) -> str:
    """Build evaluation context for technical interviews."""

    tech = context_packet.get("technical_problem", {})
    solution_approach = tech.get("solution_approach", "")
    expected_complexity = tech.get("expected_complexity", "")
    common_pitfalls = tech.get("common_pitfalls", [])
    edge_cases = tech.get("edge_cases", [])

    pitfalls_text = "\n".join(f"- {p}" for p in common_pitfalls) if common_pitfalls else "None"
    edges_text = "\n".join(f"- {e}" for e in edge_cases) if edge_cases else "None"

    return f"""---

## EVALUATION CONTEXT: Technical Interview

**Solution Approach (what good looks like):**
{solution_approach}

**Expected Complexity:** {expected_complexity if expected_complexity else "Not specified"}

**Common Pitfalls to Watch For:**
{pitfalls_text}

**Edge Cases They Should Consider:**
{edges_text}

---"""


def _build_legacy_evaluation_context(state: InterviewState) -> str:
    """Build evaluation context from legacy state fields."""

    root_cause = state.get("root_cause", "")
    facts = state.get("facts", {})
    facts_text = json.dumps(facts, indent=2)

    return f"""---

## EVALUATION CONTEXT

**What Good Looks Like:**
{root_cause}

**Available Facts:**
{facts_text}

---"""


def _format_calibration_examples(calibration: Dict[str, Any]) -> str:
    """Format calibration examples if available."""

    if not calibration:
        return ""

    sections = ["## CALIBRATION ANCHORS - What Each Level Sounds Like\n"]

    for level_key in ["level_5", "level_4", "level_3", "level_2", "level_1"]:
        level_data = calibration.get(level_key, {})
        if not level_data:
            continue

        # Handle both list (sounds_like examples) and dict formats
        if isinstance(level_data, list):
            level_num = level_key.split("_")[1]
            sections.append(f"**Level {level_num}:**")
            for example in level_data[:2]:
                sections.append(f'  - "{example}"')
        elif isinstance(level_data, dict):
            level_num = level_key.split("_")[1]
            name = level_data.get("name", "")
            chars = level_data.get("characteristics", "")
            sounds = level_data.get("sounds_like", [])

            sections.append(f"**Level {level_num} - {name}**")
            if chars:
                sections.append(f"Characteristics: {chars}")
            if sounds:
                sections.append("Sounds like:")
                for example in sounds[:2]:
                    sections.append(f'  - "{example}"')

        sections.append("")

    return "\n".join(sections)


def _build_competencies_section(spec: Dict[str, Any]) -> str:
    """Build the competencies to assess section."""

    competencies = spec.get("competencies", [])

    if not competencies:
        return "## COMPETENCIES TO ASSESS\n\nNo specific competencies defined."

    # Import universal rubric
    try:
        from specs.spec_schema import UNIVERSAL_RUBRIC
    except ImportError:
        UNIVERSAL_RUBRIC = {}

    sections = ["---\n\n## COMPETENCIES TO ASSESS\n"]
    sections.append("Score EACH competency independently on a 1-5 scale.\n")

    for comp in competencies:
        comp_id = comp.get("competency_id", "")
        tier = comp.get("tier", "important")

        full_comp = UNIVERSAL_RUBRIC.get(comp_id)
        if not full_comp:
            sections.append(f"### {comp_id} [{tier.upper()}]\nCompetency not found in rubric.\n")
            continue

        tier_label = {
            "critical": "CRITICAL - Must pass (level 3+) for overall pass",
            "important": "IMPORTANT - Contributes significantly to assessment",
            "bonus": "BONUS - Can elevate but not required"
        }.get(tier, tier.upper())

        sections.append(f"### {full_comp.name} [{tier_label}]")
        sections.append(f"{full_comp.description}\n")

        # Show level indicators
        sections.append("**Level Indicators:**")
        for level_num in [5, 4, 3, 2, 1]:
            level = full_comp.levels.get(level_num)
            if level:
                indicators = ", ".join(level.indicators[:2]) if level.indicators else level.description
                sections.append(f"- **{level_num} ({level.name}):** {indicators}")

        # Show flags
        all_red = list(full_comp.red_flags) + comp.get("additional_red_flags", [])
        all_green = list(full_comp.green_flags) + comp.get("additional_green_flags", [])

        if all_red:
            sections.append(f"\nRed Flags: {'; '.join(all_red[:3])}")
        if all_green:
            sections.append(f"Green Flags: {'; '.join(all_green[:3])}")

        sections.append("")

    return "\n".join(sections)


def _build_level_definitions_section() -> str:
    """Build universal level definitions."""

    return """---

## LEVEL DEFINITIONS (Apply to Each Competency)

**Level 5 - Outstanding:** Exceptional performance, exceeds expectations
**Level 4 - Strong:** Clear competence, meets high bar
**Level 3 - Adequate:** Acceptable but not distinctive
**Level 2 - Weak:** Below expectations, significant gaps
**Level 1 - Insufficient:** Does not meet minimum bar

Note: Level 0 means "not yet assessed" - only use when you have no signal for that competency yet.

---"""


def _build_action_mapping_section(heuristics: Dict[str, Any], spec: Dict[str, Any] = None) -> str:
    """Build the action mapping section, informed by heuristics and interview type."""

    hint_philosophy = heuristics.get("hint_philosophy", "")
    rescue_policy = heuristics.get("rescue_policy", "")
    interview_type = spec.get("interview_type", "case") if spec else "case"

    # First round uses different action philosophy
    if interview_type == "first_round":
        return """## ACTIONS TO RECOMMEND (First Round)

Based on your assessment, recommend one of:

**EXPLORE_DEEPER** (They mentioned something interesting)
- Guide interviewer to explore this topic further
- Ask conceptual follow-ups: "What made you approach it that way?"
- Find where their understanding naturally tapers off

**MOVE_ON** (You've found the edge of their understanding on this topic)
- They've shown their depth (or lack of it) on this topic
- Time to gracefully transition to a new area
- "That's helpful. Let me ask about..."

**REFRAME** (They seem confused or nervous)
- Rephrase the question more clearly
- Help them understand what you're asking
- "Let me ask that differently..."

**PROBE_GAP** (There's a JD requirement they haven't addressed)
- Guide conversation toward an unexplored area
- "I'm curious about your experience with..."
- Explore conceptually, don't interrogate

**WRAP_UP** (You have enough signal)
- You've explored the key areas
- Time to move toward closing
- Let them ask questions

**IMPORTANT:** This is exploratory conversation. Don't push for exact numbers. Find conceptual understanding and natural limits of knowledge through curiosity, not pressure.

---"""

    # Build rescue note based on heuristics (for case/technical)
    rescue_note = ""
    if "do not rescue" in rescue_policy.lower():
        rescue_note = "\n**IMPORTANT:** Do NOT rescue struggling candidates. Their inability to perform IS the assessment."
    elif "help" in rescue_policy.lower():
        rescue_note = f"\n**Help Philosophy:** {rescue_policy}"

    return f"""## ACTIONS TO RECOMMEND

Based on the LOWEST critical competency score, recommend one of:

**DO_NOT_HELP** (Levels 1-2 on critical competencies)
- Ask neutral questions only
- Do not hint or help
- Let them struggle - this IS the assessment

**MINIMAL_HELP** (Level 2-3, showing some struggle)
- One small nudge maximum
- Do not rescue
- Observe what they do with minimal help

**LIGHT_HELP** (Level 3, solid but stuck on execution)
- Help with execution details
- Do not help with thinking or direction
- Push for prioritization

**CHALLENGE** (Level 4, performing well)
- Push them further
- Add complexity or edge cases
- Make them defend their thinking

**LET_SHINE** (Level 5, exceptional)
- Get out of the way
- Let them demonstrate excellence
- Ask follow-ups that showcase depth
{rescue_note}

---"""


def _build_data_approval_section(spec: Dict[str, Any], heuristics: Dict[str, Any]) -> str:
    """Build data approval rules based on interview type."""

    interview_type = spec.get("interview_type", "case")
    data_revelation = heuristics.get("data_revelation", "")

    if interview_type == "first_round":
        return """## DATA APPROVAL (First Round)

The candidate's CV is the data. You don't need to "approve" sharing it.

Instead, guide the interviewer to:
- Probe specific claims for depth
- Ask for concrete examples and numbers
- Challenge vague answers with follow-ups
- Redirect surface-level responses to specifics

---"""

    elif interview_type == "technical":
        return f"""## DATA APPROVAL (Technical)

**Data Philosophy:** {data_revelation}

- Problem details: Always available - answer clarifying questions
- Hints: Use tiered approach - note when hints are given
- Test cases: Can provide to help them verify
- Solution: Never reveal directly

---"""

    else:  # case interview
        return f"""## DATA APPROVAL (Case Interview)

**Data Philosophy:** {data_revelation}

Only approve data for sharing when the candidate has EARNED it:

1. **Earned**: They stated a hypothesis AND asked specifically what data they need AND explained why
   → Approve the relevant data

2. **Partially earned**: They asked for specific data but without clear hypothesis
   → Approve limited data, note the gap

3. **Not earned**: Vague request or fishing expedition
   → Do not approve. Interviewer should ask what specifically they want to know.

---"""


def _build_output_format_section(spec: Dict[str, Any]) -> str:
    """Build the output format section with competency scores."""

    competencies = spec.get("competencies", [])
    comp_ids = [c.get("competency_id", "") for c in competencies]
    interview_type = spec.get("interview_type", "case")

    # Build competency scores example
    scores_example = ",\n        ".join([
        f'"{cid}": {{"level": 3, "evidence": "specific observation", "flags": []}}'
        for cid in comp_ids[:3]
    ])
    if len(comp_ids) > 3:
        scores_example += ",\n        ..."

    # Different action options for first round
    if interview_type == "first_round":
        action_options = "EXPLORE_DEEPER|MOVE_ON|REFRAME|PROBE_GAP|WRAP_UP"
    else:
        action_options = "DO_NOT_HELP|MINIMAL_HELP|LIGHT_HELP|CHALLENGE|LET_SHINE"

    return f"""## OUTPUT FORMAT

You MUST respond with valid JSON:

```json
{{
    "competency_scores": {{
        {scores_example}
    }},
    "overall_assessment": "<brief summary of where they stand>",
    "action": "<{action_options}>",
    "interviewer_guidance": "<specific instruction for how interviewer should respond>",
    "data_to_share": "<specific data approved for sharing, or null if none>",
    "focus_next": "<which competency needs more signal>"
}}
```

**Competency Score Format:**
- `level`: 0-5 (0 if not yet assessed)
- `evidence`: Specific observation from their response
- `flags`: Any red or green flags observed for this competency

---"""


def _build_critical_rules_section(heuristics: Dict[str, Any], spec: Dict[str, Any] = None) -> str:
    """Build critical rules for the evaluator."""

    interview_type = spec.get("interview_type", "case") if spec else "case"

    # First round has different critical rules
    if interview_type == "first_round":
        return """## CRITICAL RULES (First Round)

1. **You are the assessment authority.** Guide the interviewer on what to explore next.

2. **This is EXPLORATORY CONVERSATION, not interrogation.**
   - Never push for exact numbers or metrics
   - Test conceptual understanding through natural questions
   - Find where knowledge naturally tapers off

3. **Move SLOWLY through topics.**
   - One topic at a time
   - Follow threads of interesting responses
   - When you find the edge of understanding, that's the signal - move on

4. **Score based on UNDERSTANDING, not recall.**
   - Can they explain WHY they did things?
   - Do they understand trade-offs and reasoning?
   - Surface exposure vs. genuine depth

5. **Be specific in guidance.** Tell the interviewer exactly what to ask or explore next.

6. **Graceful transitions.** When moving topics, suggest smooth language: "That's helpful. I'm curious about..."

7. **No pressure or gotcha questions.** This round is about understanding who they are, not tripping them up."""

    hint_philosophy = heuristics.get("hint_philosophy", "")

    rescue_rule = "2. **DO NOT RESCUE** struggling candidates unless heuristics explicitly allow it."
    if "tiered hints" in hint_philosophy.lower():
        rescue_rule = "2. **TIERED HINTS:** First hint free, subsequent hints affect scoring. Track hint usage."

    return f"""## CRITICAL RULES

1. **You are the ONLY assessment authority.** The interviewer follows your guidance.

{rescue_rule}

3. **Score each competency independently.** A candidate can be strong in one area and weak in another.

4. **Be specific in guidance.** Don't say "push them" - say exactly what the interviewer should do or ask.

5. **Track evidence.** Every score must have specific behavioral evidence from their response.

6. **Critical competencies gate the outcome.** If ANY critical competency is below level 3, the candidate cannot pass overall."""
