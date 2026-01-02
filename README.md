# Adaptive Interview System

## What This Project Does

This is an AI-powered candidate assessment system that conducts structured interviews across multiple formats: case interviews, first-round screenings, and technical assessments. It evaluates candidates in real-time using multi-dimensional competency scoring and adapts its behavior based on demonstrated performance.

**Core Innovation**: The **Context Injection** architecture - one interviewer agent that adapts based on the context it receives. Like a method actor, the same agent delivers different interview experiences by reading from an **InterviewSpec** that defines competencies, heuristics, and behavioral guidance.

## Goals

1. **Multi-Format Interviews**: Support case interviews, first-round CV screens, and technical interviews with a unified architecture
2. **Multi-Competency Assessment**: Score candidates across multiple dimensions with tiered importance (critical, important, bonus)
3. **Objective Assessment**: Score against explicit rubrics from a Universal Rubric library
4. **Adaptive Difficulty**: Challenge strong candidates; don't rescue weak ones
5. **Natural Conversation**: Feel like a real interview, not a test

## Architecture Overview

```
                         ┌─────────────────────────────────────┐
                         │          InterviewSpec              │
                         │  (The "Script" for the Interview)   │
                         │                                     │
                         │  • Context Packet (CV/Case/Problem) │
                         │  • Selected Competencies + Tiers    │
                         │  • Interviewer Heuristics           │
                         │  • Phase Configuration              │
                         └───────────────┬─────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            InterviewState                                    │
│                (Shared state flowing through all agents)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│   Interviewer   │             │    Evaluator    │             │     Manager     │
│                 │             │                 │             │                 │
│ • Talks to      │             │ • Multi-dim     │             │ • Time limits   │
│   candidate     │             │   competency    │             │ • Competency    │
│ • Reads from    │             │   scoring       │             │   coverage      │
│   spec for      │             │ • Evidence-     │             │ • Phase         │
│   behavior      │             │   based levels  │             │   suggestions   │
│ • Adapts to     │             │ • Tiered        │             │ • Focus area    │
│   interview     │             │   pass/fail     │             │   guidance      │
│   type          │             │   logic         │             │                 │
└─────────────────┘             └─────────────────┘             └─────────────────┘
```

## Interview Types

The system supports three interview types, each with its own context packet and competency set:

| Type | Context Packet | Competencies | Use Case |
|------|---------------|--------------|----------|
| **Case** | Case prompt, facts, root cause | Problem Structuring, Analytical Reasoning, Quantitative, Synthesis, Business Judgment | Management consulting case interviews |
| **First Round** | CV, Job Description, role context | Communication, Experience Depth, Self-Awareness, Role Motivation, Business Judgment | Initial CV screening interviews |
| **Technical** | Problem statement, test cases, hints | Problem Decomposition, Code Quality, Testing Mindset, Technical Communication, Complexity Analysis | Coding/technical interviews |

## The Universal Rubric

All competencies draw from a **Universal Rubric Library** (`specs/spec_schema.py`). This ensures consistent scoring across interview types:

### Competency Tiers

| Tier | Meaning | Impact on Overall Score |
|------|---------|------------------------|
| **CRITICAL** | Must achieve level 3+ to pass | Failing any critical competency caps overall score |
| **IMPORTANT** | Core assessment dimensions | Contributes significantly to overall score |
| **BONUS** | Differentiates good from great | Can elevate but cannot carry |

### The 5-Level Scale

All competencies use the same 1-5 scale:

| Level | Name | Description |
|-------|------|-------------|
| 5 | Outstanding | Exceptional performance, exceeds expectations |
| 4 | Strong | Solid, would recommend |
| 3 | Adequate | Meets minimum bar, some concerns |
| 2 | Weak | Below expectations, significant gaps |
| 1 | Insufficient | Does not meet basic requirements |

## Agent Responsibilities

### Evaluator Agent (`agents/evaluator.py`)

The assessment authority. Scores each competency independently.

**What it does:**
- Assesses each competency in the spec with evidence-based scoring
- Tracks confidence levels (low/medium/high) based on evidence accumulation
- Provides action guidance: `DO_NOT_HELP`, `MINIMAL_HELP`, `LIGHT_HELP`, `CHALLENGE`, `LET_SHINE`
- Outputs structured guidance for the interviewer

**Key calibration:**
- Temperature: 0.3 (balanced scoring)
- Runs before every interviewer response
- Multi-competency output when spec is present

### Interviewer Agent (`agents/interviewer.py`)

The candidate-facing conversation partner. A "Method Actor" that adapts to the interview type.

**What it does:**
- Reads heuristics from the spec to adapt behavior
- Follows evaluator guidance for help levels
- Adapts opening/closing to interview type
- Reveals data only when candidates earn it (for case interviews)

**Heuristics it reads:**
- `tone` - Professional warmth level
- `hint_philosophy` - When/how to give hints
- `rescue_policy` - Never rescue weak candidates
- `pushback_style` - How to challenge strong candidates
- `data_revelation` - Rules for sharing information

### Manager Agent (`agents/manager.py`)

Session orchestration and competency coverage tracking.

**What it does:**
- Checks hard constraints (time, max exchanges)
- Monitors which competencies need more signal
- Suggests phase transitions (fluid, not enforced)
- Provides focus area guidance to interviewer

**Key outputs:**
- `urgency`: `normal` | `wrap_up_soon` | `must_end`
- `undercovered_competencies`: List of competencies needing more evidence
- `suggested_phase`: Soft suggestions for phase transitions

## The InterviewSpec System

An `InterviewSpec` is the complete "script" for an interview:

```python
InterviewSpec(
    spec_id="case_coffee_001",
    interview_type=InterviewType.CASE,
    title="Coffee Shop Profitability",

    # What the interviewer "sees"
    context_packet=ContextPacket(
        packet_type=ContextPacketType.CASE_STUDY,
        case_study=CaseStudyContext(
            case_prompt="Your client is a coffee chain...",
            facts={...},
            root_cause="..."
        )
    ),

    # Which competencies to assess and their importance
    competencies=[
        SelectedCompetency(competency_id="problem_structuring", tier=CompetencyTier.CRITICAL),
        SelectedCompetency(competency_id="analytical_reasoning", tier=CompetencyTier.CRITICAL),
        SelectedCompetency(competency_id="synthesis_recommendation", tier=CompetencyTier.IMPORTANT),
    ],

    # How the interviewer should behave
    heuristics=InterviewerHeuristics(
        tone="Professional but warm",
        hint_philosophy="Never hint on structure, only execution",
        rescue_policy="Do not rescue struggling candidates",
        ...
    ),

    # Interview phases
    phases=[
        PhaseConfig(id="structuring", name="Structuring", ...),
        PhaseConfig(id="analysis", name="Analysis", ...),
        PhaseConfig(id="synthesis", name="Synthesis", ...),
    ],

    # Session limits
    constraints=SessionConstraints(
        max_duration_minutes=30,
        max_exchanges=15
    )
)
```

## File Structure

```
adaptive_interview/
├── main.py                     # CLI entry point
├── state.py                    # InterviewState + CompetencyScore definitions
├── graph.py                    # LangGraph orchestration
├── case_loader.py              # Load legacy case JSON files
│
├── agents/
│   ├── evaluator.py            # Multi-competency scoring agent
│   ├── interviewer.py          # Candidate-facing agent (Method Actor)
│   ├── manager.py              # Session orchestration (NEW)
│   └── director.py             # Deprecated alias for manager
│
├── prompts/
│   ├── prompt_builder.py       # Spec-driven prompt generation (NEW)
│   ├── evaluator_prompt.py     # Legacy evaluator prompt
│   ├── evaluator_prompt_builder.py  # Spec-aware evaluator prompts
│   └── interviewer_prompt.py   # Legacy interviewer prompt
│
├── specs/                      # NEW - Interview Specification System
│   ├── spec_schema.py          # InterviewSpec + Universal Rubric
│   ├── spec_loader.py          # Create specs from templates/cases
│   ├── generators/
│   │   └── first_round_generator.py  # LLM-powered spec generation
│   └── templates/
│       ├── case_interview_template.json
│       └── technical_interview_template.json
│
├── cases/                      # Legacy case files (still supported)
│   ├── coffee_profitability.json
│   └── market_entry.json
│
├── api/                        # FastAPI backend
│   ├── main.py
│   └── routes/
│       └── interview.py
│
├── candidate-app/              # React candidate interface
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
└── ui/
    └── reviewer_dashboard.py   # Streamlit reviewer interface
```

## Creating Interview Specs

### From a Legacy Case File

```python
from specs import create_case_interview_spec
from case_loader import load_case

case_data = load_case("coffee_profitability")
spec = create_case_interview_spec(case_data)
```

### Generate a First-Round Spec from CV/JD

```python
from specs import generate_first_round_spec

spec = generate_first_round_spec(
    job_description="We're looking for a Senior PM...",
    candidate_cv="John Doe has 5 years experience...",
    role_title="Senior Product Manager"
)
# The LLM parses the JD/CV and generates targeted probes
```

### From a Template

```python
from specs import load_template, create_technical_interview_spec

template = load_template("technical_interview")
spec = create_technical_interview_spec(
    problem_statement="Given an array of integers...",
    test_cases=[...],
    expected_complexity="O(n)"
)
```

## Two Interfaces

### 1. Candidate App (`candidate-app/`)
**What candidates see during interviews.**

- Clean, professional chat interface
- No visible scoring or assessment information
- Adapts to interview type (case prompt vs conversational opening)

### 2. Reviewer Dashboard (`ui/reviewer_dashboard.py`)
**Internal tool for reviewing assessments.**

- Real-time competency scores by dimension
- Evidence and confidence levels for each competency
- Red/green flags as they accumulate
- Manager guidance and urgency indicators

## Running the System

### Option 1: Candidate App (React + FastAPI)

```bash
# Terminal 1: Start the API server
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start the React app
cd candidate-app
npm install    # First time only
npm run dev
```

Open http://localhost:5173 for the candidate interface.

### Option 2: Reviewer Dashboard (Streamlit)

```bash
streamlit run ui/reviewer_dashboard.py
```

### Option 3: CLI Mode

```bash
python main.py                       # Interactive case selection
python main.py coffee_profitability  # Run specific case
python main.py --list                # List available cases
```

## Key Design Principles

### 1. Context Injection (Method Actor)
One interviewer agent, multiple behaviors. The spec is the script.

### 2. Multi-Dimensional Assessment
Each competency scored independently. No single-score bottleneck.

### 3. Tiered Pass/Fail Logic
Critical competencies gate overall pass. Bonus competencies differentiate.

### 4. Evidence-Based Scoring
Confidence levels track how much signal we have per competency.

### 5. Non-Rescuing
Level 1-2 candidates are not helped. Struggle is signal.

### 6. Fluid Phases
Manager suggests phase transitions; interviewer decides organically.

## Calibration Workflow

1. **Adjust Universal Rubric** (`specs/spec_schema.py`)
   - Add competencies to the library
   - Update level indicators

2. **Tune Interview Templates** (`specs/templates/`)
   - Adjust default heuristics
   - Configure phase structures

3. **Case-Specific Calibration** (in specs or case files)
   - Add case-specific indicators
   - Override heuristics for specific interviews

4. **Tune Prompt Builders** (`prompts/prompt_builder.py`)
   - Adjust how specs translate to prompts

## Dependencies

### Python (Backend)
- `langgraph>=0.2.0` - Agent graph orchestration
- `langchain-anthropic>=0.2.0` - Claude LLM integration
- `pydantic>=2.0.0` - Spec validation
- `fastapi>=0.109.0` - API server
- `uvicorn>=0.27.0` - ASGI server
- `streamlit>=1.38.0` - Reviewer dashboard
- Claude Sonnet 4 (`claude-sonnet-4-20250514`) - All agents

### Node.js (Candidate App)
- React 18
- Vite 5
- Tailwind CSS 3

## Environment Setup

```bash
# Create .env file
ANTHROPIC_API_KEY=your_key_here

# Install Python dependencies
pip install langgraph langchain-anthropic pydantic fastapi uvicorn streamlit

# Install React dependencies
cd candidate-app
npm install
```
