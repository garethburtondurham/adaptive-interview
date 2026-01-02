"""
Interview Specification Schema

This module defines the data structures for the Context Injection architecture.
The core principle: ONE interviewer agent that adapts based on what context it receives.

Key concepts:
- InterviewSpec: Complete specification for an interview session
- ContextPacket: What the interviewer "sees" (CV, case, problem)
- Universal Rubric: Standard competencies that cases select from
- Heuristics: Behavioral guidance that replaces hard-coded rules
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


# =============================================================================
# ENUMS FOR TYPE SAFETY
# =============================================================================

class InterviewType(str, Enum):
    FIRST_ROUND = "first_round"
    CASE = "case"
    TECHNICAL = "technical"


class ContextPacketType(str, Enum):
    CV_SCREEN = "cv_screen"
    CASE_STUDY = "case_study"
    TECHNICAL_PROBLEM = "technical_problem"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Urgency(str, Enum):
    NORMAL = "normal"
    WRAP_UP_SOON = "wrap_up_soon"
    MUST_END = "must_end"


class CompetencyTier(str, Enum):
    """
    Tiered competency system:
    - CRITICAL: Must achieve level 3+ to pass overall
    - IMPORTANT: Contributes significantly to assessment
    - BONUS: Nice-to-have, can elevate a good candidate to great
    """
    CRITICAL = "critical"
    IMPORTANT = "important"
    BONUS = "bonus"


# =============================================================================
# UNIVERSAL RUBRIC LIBRARY
# =============================================================================
# Standard competencies that any interview type can select from.
# Each case/interview specifies which competencies apply and their tier.

class RubricLevel(BaseModel):
    """What a specific level looks like for a competency"""
    level: int  # 1-5
    name: str  # e.g., "Outstanding", "Strong", "Adequate", "Weak", "Insufficient"
    description: str  # What this level looks like
    indicators: List[str] = Field(default_factory=list)  # Observable behaviors


class UniversalCompetency(BaseModel):
    """
    A competency definition in the universal rubric library.
    These are interview-type-agnostic definitions.
    """
    id: str  # e.g., "problem_structuring"
    name: str  # Display name
    description: str  # What this competency assesses

    # Universal rubric levels (same 1-5 scale for all competencies)
    levels: Dict[int, RubricLevel]  # 1-5 mapping

    # Signal patterns
    red_flags: List[str] = Field(default_factory=list)
    green_flags: List[str] = Field(default_factory=list)

    # Which interview types this competency applies to
    applicable_types: List[InterviewType] = Field(default_factory=list)


# The universal rubric - populated at module load time
UNIVERSAL_RUBRIC: Dict[str, UniversalCompetency] = {}


def _build_universal_rubric() -> Dict[str, UniversalCompetency]:
    """Build the universal rubric library with all standard competencies"""

    rubric = {}

    # =========================================================================
    # CASE INTERVIEW COMPETENCIES
    # =========================================================================

    rubric["problem_structuring"] = UniversalCompetency(
        id="problem_structuring",
        name="Problem Structuring",
        description="Ability to break down ambiguous problems into logical, MECE components",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Creates novel, insightful framework perfectly tailored to the problem",
                indicators=[
                    "Identifies non-obvious problem dimensions",
                    "Framework reveals strategic tensions",
                    "Prioritizes ruthlessly with clear rationale",
                    "Adapts structure fluidly as information emerges"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Solid, logical structure that covers key dimensions",
                indicators=[
                    "MECE breakdown of problem",
                    "Clear prioritization of areas",
                    "Explains reasoning behind structure",
                    "Structure guides productive analysis"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Basic structure present but may miss dimensions or lack prioritization",
                indicators=[
                    "Attempts to break down problem",
                    "Covers obvious dimensions",
                    "Some logical flow",
                    "May need prompting to prioritize"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Minimal structure, jumps to analysis without framework",
                indicators=[
                    "Lists topics rather than structures",
                    "No clear prioritization",
                    "Misses major dimensions",
                    "Framework doesn't guide analysis"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No meaningful structure, chaotic approach",
                indicators=[
                    "Dives into random details",
                    "No attempt to organize thinking",
                    "Cannot articulate approach",
                    "Struggles when asked to step back"
                ]
            )
        },
        red_flags=[
            "Uses generic framework without tailoring",
            "Cannot explain why structure fits this problem",
            "Abandons structure immediately when challenged"
        ],
        green_flags=[
            "Creates custom framework for the specific problem",
            "Explicitly deprioritizes areas with reasoning",
            "Structure reveals insight about problem nature"
        ],
        applicable_types=[InterviewType.CASE]
    )

    rubric["analytical_reasoning"] = UniversalCompetency(
        id="analytical_reasoning",
        name="Analytical Reasoning",
        description="Ability to draw logical conclusions from data and identify patterns",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Extracts non-obvious insights, synthesizes across data sources",
                indicators=[
                    "Identifies second-order implications",
                    "Connects disparate data points",
                    "Challenges assumptions in data",
                    "Generates testable hypotheses"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Clear logical reasoning, appropriate conclusions from data",
                indicators=[
                    "Interprets data correctly",
                    "Draws reasonable conclusions",
                    "Identifies key drivers",
                    "Acknowledges limitations"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Basic analysis present but may miss nuances",
                indicators=[
                    "Can work with data when provided",
                    "Draws obvious conclusions",
                    "May need help seeing implications",
                    "Analysis is surface-level"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Struggles to interpret data or draws wrong conclusions",
                indicators=[
                    "Misreads data",
                    "Conclusions don't follow from evidence",
                    "Ignores contradictory information",
                    "Cannot explain reasoning"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot perform basic analysis",
                indicators=[
                    "Overwhelmed by data",
                    "No logical reasoning present",
                    "Makes random assertions",
                    "Cannot engage with analytical questions"
                ]
            )
        },
        red_flags=[
            "Conclusion contradicts the data provided",
            "Ignores inconvenient data points",
            "Cannot explain the 'so what' of analysis"
        ],
        green_flags=[
            "Proactively stress-tests own conclusions",
            "Asks for specific data to test hypotheses",
            "Identifies what would change their view"
        ],
        applicable_types=[InterviewType.CASE, InterviewType.TECHNICAL]
    )

    rubric["quantitative_reasoning"] = UniversalCompetency(
        id="quantitative_reasoning",
        name="Quantitative Reasoning",
        description="Ability to work with numbers, make estimates, and perform calculations",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Elegant quantitative approach, comfortable with ambiguity in numbers",
                indicators=[
                    "Structures calculations for insight",
                    "Sanity-checks results instinctively",
                    "Uses estimation creatively",
                    "Translates numbers to business meaning"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Accurate calculations, sensible estimates",
                indicators=[
                    "Sets up problems correctly",
                    "Arithmetic is accurate",
                    "Makes reasonable assumptions",
                    "Catches own errors"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Can do calculations but may make errors or need guidance",
                indicators=[
                    "Basic math skills present",
                    "May make computational errors",
                    "Needs help structuring quant problems",
                    "Can work through with some support"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Struggles with quantitative aspects",
                indicators=[
                    "Frequent calculation errors",
                    "Cannot structure quant problems",
                    "Unreasonable estimates",
                    "Avoids numerical analysis"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot engage with quantitative elements",
                indicators=[
                    "Freezes on math",
                    "Cannot make basic estimates",
                    "Numbers seem random",
                    "No numerical intuition"
                ]
            )
        },
        red_flags=[
            "Off by order of magnitude without noticing",
            "Cannot set up basic percentage/ratio calculations",
            "Refuses to estimate when exact data unavailable"
        ],
        green_flags=[
            "Proactively sanity-checks calculations",
            "Comfortable with back-of-envelope estimation",
            "Uses ranges and sensitivity analysis"
        ],
        applicable_types=[InterviewType.CASE, InterviewType.TECHNICAL]
    )

    rubric["synthesis_recommendation"] = UniversalCompetency(
        id="synthesis_recommendation",
        name="Synthesis & Recommendation",
        description="Ability to synthesize analysis into clear, actionable recommendations",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="CEO-ready recommendation with clear logic, risks, and next steps",
                indicators=[
                    "Crisp, confident recommendation",
                    "Acknowledges key risks and mitigations",
                    "Prioritized implementation steps",
                    "Anticipates stakeholder concerns"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Clear recommendation supported by analysis",
                indicators=[
                    "Takes a clear position",
                    "Links back to analysis",
                    "Identifies key risks",
                    "Actionable next steps"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Has a recommendation but may lack conviction or completeness",
                indicators=[
                    "Provides an answer",
                    "Some supporting logic",
                    "May hedge excessively",
                    "Next steps vague"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Unclear or unsupported recommendation",
                indicators=[
                    "Cannot commit to position",
                    "Recommendation contradicts analysis",
                    "No implementation thinking",
                    "When pushed, falls apart"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot synthesize or make recommendation",
                indicators=[
                    "Restates facts without synthesis",
                    "No clear recommendation",
                    "Cannot answer 'so what'",
                    "Analysis and conclusion disconnected"
                ]
            )
        },
        red_flags=[
            "Recommendation contradicts own analysis",
            "Cannot prioritize when asked",
            "Presents options instead of recommendation"
        ],
        green_flags=[
            "Leads with the answer",
            "Proactively addresses risks",
            "Clear on what success looks like"
        ],
        applicable_types=[InterviewType.CASE]
    )

    rubric["business_judgment"] = UniversalCompetency(
        id="business_judgment",
        name="Business Judgment",
        description="Commercial awareness and practical business sense",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Sophisticated commercial instincts, sees business as integrated system",
                indicators=[
                    "Considers multiple stakeholders",
                    "Understands competitive dynamics",
                    "Thinks about implementation reality",
                    "Balances short and long-term"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good commercial awareness, practical thinking",
                indicators=[
                    "Considers customer perspective",
                    "Aware of competitive context",
                    "Thinks about execution",
                    "Reasonable business instincts"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Basic business awareness but may miss commercial nuances",
                indicators=[
                    "Understands basic business concepts",
                    "May miss stakeholder impacts",
                    "Analysis somewhat academic",
                    "Limited competitive awareness"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Limited commercial awareness",
                indicators=[
                    "Ignores business realities",
                    "Recommendations impractical",
                    "No stakeholder consideration",
                    "Thinks in abstractions"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No business sense evident",
                indicators=[
                    "Completely academic approach",
                    "No understanding of business context",
                    "Recommendations naive",
                    "Cannot engage with commercial questions"
                ]
            )
        },
        red_flags=[
            "Ignores obvious implementation barriers",
            "Treats all stakeholders as having aligned interests",
            "No awareness of competitive dynamics"
        ],
        green_flags=[
            "Proactively considers implementation challenges",
            "Asks about organizational constraints",
            "Thinks about customer and competitive response"
        ],
        applicable_types=[InterviewType.CASE, InterviewType.FIRST_ROUND]
    )

    # =========================================================================
    # FIRST ROUND COMPETENCIES
    # =========================================================================

    rubric["communication"] = UniversalCompetency(
        id="communication",
        name="Communication",
        description="Clarity, structure, and effectiveness of verbal communication",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Exceptionally clear, engaging, adapts to audience perfectly",
                indicators=[
                    "Complex ideas explained simply",
                    "Compelling narrative structure",
                    "Reads and responds to cues",
                    "Concise yet complete"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Clear, well-organized communication",
                indicators=[
                    "Easy to follow",
                    "Good structure to responses",
                    "Appropriate level of detail",
                    "Confident delivery"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Communicates adequately but may ramble or lack structure",
                indicators=[
                    "Gets point across eventually",
                    "Some structure present",
                    "May need to be redirected",
                    "Occasional unclear moments"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Difficult to follow or overly brief",
                indicators=[
                    "Hard to understand main point",
                    "No structure to responses",
                    "Either too verbose or too terse",
                    "Doesn't answer questions asked"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot communicate effectively",
                indicators=[
                    "Incoherent responses",
                    "Cannot articulate thoughts",
                    "Completely misses questions",
                    "Communication breakdown"
                ]
            )
        },
        red_flags=[
            "Cannot give a straight answer to direct questions",
            "Rambles for minutes without making a point",
            "Uses jargon to obscure lack of substance"
        ],
        green_flags=[
            "Answers question directly then elaborates",
            "Signals structure ('Three things...')",
            "Asks clarifying questions when appropriate"
        ],
        applicable_types=[InterviewType.FIRST_ROUND, InterviewType.CASE, InterviewType.TECHNICAL]
    )

    rubric["experience_depth"] = UniversalCompetency(
        id="experience_depth",
        name="Experience Depth",
        description="Genuine depth of experience vs surface-level exposure",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Deep, hands-on experience with clear ownership and impact",
                indicators=[
                    "Can go multiple levels deep on any topic",
                    "Specific numbers and outcomes",
                    "Clear personal contribution",
                    "Learned from failures too"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Solid experience with good depth in key areas",
                indicators=[
                    "Can elaborate on most claims",
                    "Specific examples available",
                    "Clear role in outcomes",
                    "Reasonable depth on probing"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Has experience but depth is uneven",
                indicators=[
                    "Some areas have good depth",
                    "Other areas surface-level",
                    "May have been peripheral on some projects",
                    "Can go deeper with prompting"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Experience appears exaggerated or shallow",
                indicators=[
                    "Cannot provide specifics",
                    "Stories don't hold up to probing",
                    "Unclear personal contribution",
                    "Vague on details"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Claims not supported by evidence",
                indicators=[
                    "Stories contradict each other",
                    "Cannot answer basic questions about own work",
                    "Obvious exaggeration",
                    "No credible experience"
                ]
            )
        },
        red_flags=[
            "Story changes when probed from different angles",
            "Uses 'we' exclusively, cannot articulate own contribution",
            "Metrics don't pass basic sanity checks"
        ],
        green_flags=[
            "Readily shares specific numbers and outcomes",
            "Acknowledges limitations and what they'd do differently",
            "Can explain the 'why' behind decisions"
        ],
        applicable_types=[InterviewType.FIRST_ROUND]
    )

    rubric["self_awareness"] = UniversalCompetency(
        id="self_awareness",
        name="Self-Awareness",
        description="Accurate understanding of own strengths, weaknesses, and impact",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Exceptional self-awareness, genuinely reflective",
                indicators=[
                    "Accurately assesses own strengths and gaps",
                    "Specific examples of learning from failure",
                    "Understands own impact on others",
                    "Growth mindset evident"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good self-awareness, can discuss development areas",
                indicators=[
                    "Honest about weaknesses",
                    "Can give real failure examples",
                    "Shows learning and adaptation",
                    "Reasonable self-assessment"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Some self-awareness but may be limited",
                indicators=[
                    "Can discuss weaknesses if pushed",
                    "Failures tend to be 'safe' examples",
                    "Limited reflection depth",
                    "May overstate or understate abilities"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Limited self-awareness",
                indicators=[
                    "Weaknesses are strengths in disguise",
                    "Blames others for failures",
                    "Cannot articulate development areas",
                    "Self-assessment doesn't match evidence"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No self-awareness evident",
                indicators=[
                    "Delusional about abilities",
                    "Cannot acknowledge any weakness",
                    "No learning from past evident",
                    "Defensive when probed"
                ]
            )
        },
        red_flags=[
            "Every failure was someone else's fault",
            "'Weakness' is actually a humble brag",
            "Self-assessment wildly inconsistent with evidence"
        ],
        green_flags=[
            "Volunteers genuine weakness without being asked",
            "Can explain specific feedback received and actions taken",
            "Asks thoughtful questions about role fit"
        ],
        applicable_types=[InterviewType.FIRST_ROUND]
    )

    rubric["role_motivation"] = UniversalCompetency(
        id="role_motivation",
        name="Role & Company Motivation",
        description="Genuine interest in this specific role and company",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Deeply researched, compelling fit narrative",
                indicators=[
                    "Specific reasons for this company",
                    "Clear career logic leading here",
                    "Has talked to people at company",
                    "Asks insightful questions"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good understanding of role and company, clear motivation",
                indicators=[
                    "Has done research",
                    "Can articulate why this role",
                    "Reasonable career narrative",
                    "Thoughtful questions"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Basic understanding and motivation",
                indicators=[
                    "General interest evident",
                    "Some company knowledge",
                    "Motivation somewhat generic",
                    "Surface-level questions"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Limited research or motivation unclear",
                indicators=[
                    "Couldn't name company specifics",
                    "Role could be anywhere",
                    "No clear career logic",
                    "Questions are generic"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No genuine interest evident",
                indicators=[
                    "Knows nothing about company",
                    "Cannot articulate why here",
                    "No questions to ask",
                    "Going through the motions"
                ]
            )
        },
        red_flags=[
            "Cannot name what company actually does",
            "Story about why this role doesn't make sense",
            "No questions for interviewer"
        ],
        green_flags=[
            "References specific company initiatives or values",
            "Career narrative clearly leads to this role",
            "Questions reveal genuine thought about the role"
        ],
        applicable_types=[InterviewType.FIRST_ROUND]
    )

    # =========================================================================
    # TECHNICAL INTERVIEW COMPETENCIES
    # =========================================================================

    rubric["problem_decomposition"] = UniversalCompetency(
        id="problem_decomposition",
        name="Problem Decomposition",
        description="Breaking down technical problems into solvable components",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Elegant decomposition, identifies optimal subproblems",
                indicators=[
                    "Identifies clean abstractions",
                    "Sees reusable components",
                    "Considers edge cases upfront",
                    "Decomposition enables parallel work"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good decomposition, logical components",
                indicators=[
                    "Breaks problem into clear parts",
                    "Reasonable interfaces between parts",
                    "Tackles complexity incrementally",
                    "Good instinct for what's hard"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Can decompose but may miss optimal structure",
                indicators=[
                    "Attempts to break down problem",
                    "Components somewhat coupled",
                    "May need hints for better structure",
                    "Gets there eventually"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Struggles to decompose, monolithic thinking",
                indicators=[
                    "Tries to solve everything at once",
                    "Cannot identify subproblems",
                    "No clear approach",
                    "Gets lost in details"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot break down problems",
                indicators=[
                    "No decomposition attempted",
                    "Completely overwhelmed",
                    "Cannot identify where to start",
                    "Random attempts"
                ]
            )
        },
        red_flags=[
            "Starts coding before understanding the problem",
            "Cannot explain approach at high level",
            "Components are tightly coupled"
        ],
        green_flags=[
            "Draws out problem structure before coding",
            "Identifies helper functions proactively",
            "Thinks about interfaces and contracts"
        ],
        applicable_types=[InterviewType.TECHNICAL]
    )

    rubric["code_quality"] = UniversalCompetency(
        id="code_quality",
        name="Code Quality",
        description="Clean, readable, maintainable code",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Production-quality code, excellent style",
                indicators=[
                    "Clean, idiomatic code",
                    "Good naming and structure",
                    "Handles edge cases gracefully",
                    "Would pass code review easily"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good quality code, minor issues only",
                indicators=[
                    "Readable and well-organized",
                    "Reasonable naming",
                    "Mostly handles edge cases",
                    "Would pass with minor comments"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Working code but quality issues present",
                indicators=[
                    "Code works but messy",
                    "Some naming issues",
                    "Edge cases handled inconsistently",
                    "Needs cleanup before merge"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Poor code quality, hard to follow",
                indicators=[
                    "Code is confusing",
                    "Poor naming throughout",
                    "Edge cases ignored",
                    "Would not pass review"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Code doesn't work or is incomprehensible",
                indicators=[
                    "Syntax errors",
                    "Logic fundamentally broken",
                    "Cannot explain own code",
                    "Not functional"
                ]
            )
        },
        red_flags=[
            "Magic numbers everywhere",
            "Functions doing multiple things",
            "Cannot explain what code does"
        ],
        green_flags=[
            "Refactors proactively when seeing mess",
            "Asks about code style preferences",
            "Writes self-documenting code"
        ],
        applicable_types=[InterviewType.TECHNICAL]
    )

    rubric["testing_mindset"] = UniversalCompetency(
        id="testing_mindset",
        name="Testing Mindset",
        description="Thinking about correctness, edge cases, and verification",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Thorough testing approach, catches edge cases proactively",
                indicators=[
                    "Identifies edge cases before coding",
                    "Writes tests alongside code",
                    "Thinks about failure modes",
                    "Good test coverage instinct"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good testing awareness, catches most edge cases",
                indicators=[
                    "Tests code as they go",
                    "Identifies common edge cases",
                    "Fixes bugs when found",
                    "Reasonable coverage"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Some testing awareness but not comprehensive",
                indicators=[
                    "Tests happy path",
                    "Misses some edge cases",
                    "Tests when prompted",
                    "Basic verification"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Limited testing awareness",
                indicators=[
                    "Doesn't test until asked",
                    "Misses obvious edge cases",
                    "Surprised by failures",
                    "No systematic approach"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No testing mindset",
                indicators=[
                    "Cannot identify test cases",
                    "Code has obvious bugs",
                    "No verification of correctness",
                    "Defensive about bugs"
                ]
            )
        },
        red_flags=[
            "Claims code is correct without testing",
            "Cannot generate test cases when asked",
            "Surprised by obvious edge cases"
        ],
        green_flags=[
            "Asks about test cases upfront",
            "Tests as they implement",
            "Proactively identifies edge cases"
        ],
        applicable_types=[InterviewType.TECHNICAL]
    )

    rubric["technical_communication"] = UniversalCompetency(
        id="technical_communication",
        name="Technical Communication",
        description="Ability to explain technical thinking and trade-offs",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Crystal clear technical communication",
                indicators=[
                    "Explains complex ideas simply",
                    "Good use of analogies",
                    "Anticipates questions",
                    "Adapts to audience"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Clear technical explanations",
                indicators=[
                    "Easy to follow reasoning",
                    "Explains trade-offs well",
                    "Thinks aloud effectively",
                    "Good technical vocabulary"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Can explain but may need prompting",
                indicators=[
                    "Explains when asked",
                    "Sometimes hard to follow",
                    "May skip steps",
                    "Needs prompting to elaborate"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Difficult to follow technical explanations",
                indicators=[
                    "Mumbles while coding",
                    "Cannot explain approach",
                    "Jargon without clarity",
                    "Gets lost in details"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="Cannot communicate technical thinking",
                indicators=[
                    "Silent while working",
                    "Cannot explain own code",
                    "No reasoning visible",
                    "Communication breakdown"
                ]
            )
        },
        red_flags=[
            "Cannot explain why they chose an approach",
            "Gets defensive when questioned",
            "Cannot discuss complexity or trade-offs"
        ],
        green_flags=[
            "Thinks aloud naturally",
            "Discusses trade-offs unprompted",
            "Asks clarifying questions"
        ],
        applicable_types=[InterviewType.TECHNICAL]
    )

    rubric["complexity_optimization"] = UniversalCompetency(
        id="complexity_optimization",
        name="Complexity & Optimization",
        description="Understanding of algorithmic complexity and optimization",
        levels={
            5: RubricLevel(
                level=5,
                name="Outstanding",
                description="Deep complexity understanding, optimal solutions",
                indicators=[
                    "Identifies optimal complexity upfront",
                    "Can prove correctness",
                    "Knows when to optimize",
                    "Understands space-time trade-offs"
                ]
            ),
            4: RubricLevel(
                level=4,
                name="Strong",
                description="Good complexity analysis, reasonable optimization",
                indicators=[
                    "Correctly analyzes complexity",
                    "Can improve from naive solution",
                    "Understands common patterns",
                    "Good intuition for bottlenecks"
                ]
            ),
            3: RubricLevel(
                level=3,
                name="Adequate",
                description="Basic complexity awareness",
                indicators=[
                    "Knows O(n) vs O(n^2)",
                    "Can optimize with hints",
                    "May miss optimization opportunities",
                    "Basic understanding"
                ]
            ),
            2: RubricLevel(
                level=2,
                name="Weak",
                description="Limited complexity understanding",
                indicators=[
                    "Cannot analyze complexity",
                    "Writes inefficient code",
                    "No optimization instinct",
                    "Doesn't recognize bottlenecks"
                ]
            ),
            1: RubricLevel(
                level=1,
                name="Insufficient",
                description="No understanding of complexity",
                indicators=[
                    "Doesn't know Big O",
                    "Cannot discuss efficiency",
                    "No concept of scalability",
                    "Brute force only"
                ]
            )
        },
        red_flags=[
            "O(n^3) solution when O(n) exists and is obvious",
            "Cannot explain complexity of own solution",
            "No awareness of scalability"
        ],
        green_flags=[
            "Discusses complexity before coding",
            "Iterates from working to optimal",
            "Considers space complexity too"
        ],
        applicable_types=[InterviewType.TECHNICAL]
    )

    return rubric


# Initialize the universal rubric
UNIVERSAL_RUBRIC = _build_universal_rubric()


def get_competency(competency_id: str) -> Optional[UniversalCompetency]:
    """Get a competency definition from the universal rubric"""
    return UNIVERSAL_RUBRIC.get(competency_id)


def get_competencies_for_type(interview_type: InterviewType) -> List[UniversalCompetency]:
    """Get all competencies applicable to an interview type"""
    return [
        comp for comp in UNIVERSAL_RUBRIC.values()
        if interview_type in comp.applicable_types
    ]


# =============================================================================
# CONTEXT PACKETS - What the interviewer "sees"
# =============================================================================

class CVScreenContext(BaseModel):
    """Context for first-round screening interviews"""
    job_description: str
    candidate_cv: str
    role_title: str
    company_context: Optional[str] = None

    # Parsed from JD/CV by generator
    jd_requirements: List[str] = Field(default_factory=list)
    cv_claims: List[str] = Field(default_factory=list)
    gaps_to_probe: List[str] = Field(default_factory=list)
    claims_to_validate: List[str] = Field(default_factory=list)


class CaseStudyContext(BaseModel):
    """Context for case interviews"""
    case_prompt: str
    facts: Dict[str, Any]
    root_cause: str
    strong_recommendations: List[str] = Field(default_factory=list)

    # Case-specific calibration examples (supplements universal rubric)
    calibration_examples: Dict[str, List[str]] = Field(default_factory=dict)


class TechnicalProblemContext(BaseModel):
    """Context for technical/coding interviews"""
    problem_statement: str
    starter_code: Optional[str] = None
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    expected_complexity: Optional[str] = None

    # Hints available (tiered)
    available_hints: List[Dict[str, Any]] = Field(default_factory=list)

    # Solution guide
    solution_approach: str = ""
    common_pitfalls: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)


class ContextPacket(BaseModel):
    """
    The context packet - what the interviewer "sees".
    Only ONE sub-object should be populated based on packet_type.
    """
    packet_type: ContextPacketType

    cv_screen: Optional[CVScreenContext] = None
    case_study: Optional[CaseStudyContext] = None
    technical_problem: Optional[TechnicalProblemContext] = None

    def get_context(self) -> Union[CVScreenContext, CaseStudyContext, TechnicalProblemContext]:
        """Get the active context based on packet_type"""
        if self.packet_type == ContextPacketType.CV_SCREEN:
            return self.cv_screen
        elif self.packet_type == ContextPacketType.CASE_STUDY:
            return self.case_study
        elif self.packet_type == ContextPacketType.TECHNICAL_PROBLEM:
            return self.technical_problem
        raise ValueError(f"Unknown packet type: {self.packet_type}")


# =============================================================================
# COMPETENCY SELECTION & SCORING
# =============================================================================

class SelectedCompetency(BaseModel):
    """
    A competency selected for this specific interview.
    References the universal rubric but adds interview-specific config.
    """
    competency_id: str  # References UNIVERSAL_RUBRIC
    tier: CompetencyTier = CompetencyTier.IMPORTANT

    # Optional case-specific overrides/additions to the universal rubric
    additional_red_flags: List[str] = Field(default_factory=list)
    additional_green_flags: List[str] = Field(default_factory=list)
    case_specific_indicators: Dict[int, List[str]] = Field(default_factory=dict)  # level -> indicators

    def get_full_competency(self) -> UniversalCompetency:
        """Get the full competency definition, merging case-specific additions"""
        base = UNIVERSAL_RUBRIC.get(self.competency_id)
        if not base:
            raise ValueError(f"Unknown competency: {self.competency_id}")

        # Merge additional flags
        merged = base.model_copy(deep=True)
        merged.red_flags = list(base.red_flags) + self.additional_red_flags
        merged.green_flags = list(base.green_flags) + self.additional_green_flags

        # Merge case-specific indicators
        for level, indicators in self.case_specific_indicators.items():
            if level in merged.levels:
                merged.levels[level].indicators = list(merged.levels[level].indicators) + indicators

        return merged


class CompetencyScore(BaseModel):
    """Runtime score for a single competency"""
    competency_id: str
    current_level: int = 0  # 1-5, 0 = not yet assessed
    evidence: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW

    # History
    level_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Flags observed for this competency
    red_flags_observed: List[str] = Field(default_factory=list)
    green_flags_observed: List[str] = Field(default_factory=list)


# =============================================================================
# INTERVIEWER HEURISTICS
# =============================================================================

class InterviewerHeuristics(BaseModel):
    """
    Behavioral guidance - the "script" for the interviewer's personality.
    The interviewer reads these and adapts its behavior.
    """
    # Persona
    tone: str
    persona_description: str

    # Interaction style
    primary_mode: str
    silence_tolerance: str

    # Help philosophy
    hint_philosophy: str
    rescue_policy: str

    # Challenge style
    pushback_style: str
    follow_up_depth: str

    # Data/information
    data_revelation: str

    # Opening/closing
    opening_style: str
    closing_style: str


# =============================================================================
# PHASE CONFIGURATION
# =============================================================================

class PhaseConfig(BaseModel):
    """Configuration for an interview phase"""
    id: str
    name: str
    objective: str

    # Soft transition guidance (Manager suggests, doesn't enforce)
    suggested_min_exchanges: int = 0
    suggested_max_exchanges: Optional[int] = None
    transition_signals: List[str] = Field(default_factory=list)

    # Which competencies to focus on in this phase
    focus_competencies: List[str] = Field(default_factory=list)

    # Phase-specific heuristic tweaks
    heuristic_overrides: Dict[str, str] = Field(default_factory=dict)


# =============================================================================
# SESSION CONSTRAINTS
# =============================================================================

class SessionConstraints(BaseModel):
    """Hard limits on the interview session"""
    max_duration_minutes: int = 30
    max_exchanges: int = 15
    min_exchanges_for_completion: int = 5

    # Termination
    allow_early_termination: bool = True


# =============================================================================
# MANAGER DIRECTIVE
# =============================================================================

class ManagerDirective(BaseModel):
    """Output from Manager - suggestions, not commands"""
    should_continue: bool
    focus_area: Optional[str] = None
    urgency: Urgency = Urgency.NORMAL

    # Competency guidance
    undercovered_competencies: List[str] = Field(default_factory=list)
    satisfied_competencies: List[str] = Field(default_factory=list)

    # Phase suggestion (not enforcement)
    suggested_phase: Optional[str] = None
    phase_suggestion_reason: Optional[str] = None


# =============================================================================
# THE MAIN INTERVIEW SPEC
# =============================================================================

class InterviewSpec(BaseModel):
    """
    Complete specification for an interview session.
    This is the "script" that makes one interviewer behave differently
    for different interview types - the Method Actor principle.
    """
    # Metadata
    spec_id: str
    interview_type: InterviewType
    title: str
    version: str = "1.0"

    # Context packet - what the interviewer "sees"
    context_packet: ContextPacket

    # Selected competencies from universal rubric
    competencies: List[SelectedCompetency]

    # Behavioral heuristics
    heuristics: InterviewerHeuristics

    # Phase configuration
    phases: List[PhaseConfig]

    # Session constraints
    constraints: SessionConstraints

    # Traceability
    template_id: Optional[str] = None

    class Config:
        use_enum_values = True

    def get_critical_competencies(self) -> List[SelectedCompetency]:
        """Get competencies that must pass for overall pass"""
        return [c for c in self.competencies if c.tier == CompetencyTier.CRITICAL]

    def get_competency_by_id(self, competency_id: str) -> Optional[SelectedCompetency]:
        """Get a selected competency by ID"""
        for comp in self.competencies:
            if comp.competency_id == competency_id:
                return comp
        return None


# =============================================================================
# VALIDATION
# =============================================================================

def validate_spec(spec: InterviewSpec) -> List[str]:
    """Validate an interview spec and return any issues"""
    issues = []

    # Check context packet matches interview type
    expected_packet = {
        InterviewType.FIRST_ROUND: ContextPacketType.CV_SCREEN,
        InterviewType.CASE: ContextPacketType.CASE_STUDY,
        InterviewType.TECHNICAL: ContextPacketType.TECHNICAL_PROBLEM
    }

    if spec.context_packet.packet_type != expected_packet.get(spec.interview_type):
        issues.append(
            f"{spec.interview_type} interview requires {expected_packet[spec.interview_type]} "
            f"context packet, got {spec.context_packet.packet_type}"
        )

    # Check context is populated
    if spec.context_packet.packet_type == ContextPacketType.CV_SCREEN and not spec.context_packet.cv_screen:
        issues.append("cv_screen context is missing")
    elif spec.context_packet.packet_type == ContextPacketType.CASE_STUDY and not spec.context_packet.case_study:
        issues.append("case_study context is missing")
    elif spec.context_packet.packet_type == ContextPacketType.TECHNICAL_PROBLEM and not spec.context_packet.technical_problem:
        issues.append("technical_problem context is missing")

    # Check competencies exist in universal rubric
    for comp in spec.competencies:
        if comp.competency_id not in UNIVERSAL_RUBRIC:
            issues.append(f"Unknown competency: {comp.competency_id}")

    # Check at least one critical competency
    critical = [c for c in spec.competencies if c.tier == CompetencyTier.CRITICAL]
    if not critical:
        issues.append("At least one competency should be marked as CRITICAL")

    # Check phases reference valid competencies
    competency_ids = {c.competency_id for c in spec.competencies}
    for phase in spec.phases:
        for focus_comp in phase.focus_competencies:
            if focus_comp not in competency_ids:
                issues.append(f"Phase '{phase.id}' references competency '{focus_comp}' not in spec")

    return issues
