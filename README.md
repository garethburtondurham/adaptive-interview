# Adaptive Case Interview System

## What This Project Does

This is an AI-powered candidate assessment system that conducts management consulting-style case interviews. It evaluates candidates in real-time and adapts its behavior based on demonstrated performance.

**Core Innovation**: The system separates the **Evaluator** (hidden scoring brain) from the **Interviewer** (candidate-facing persona), enabling both objective assessment and natural dialogue.

## Goals

1. **Objective Assessment**: Score candidates against explicit rubrics, not interviewer intuition
2. **Adaptive Difficulty**: Challenge strong candidates; don't rescue weak ones
3. **Natural Conversation**: Feel like a real interview, not a test
4. **Transparent Scoring**: Every assessment has explicit reasoning tied to rubric criteria

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    InterviewState                        │
│         (Shared state flowing through all agents)        │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Interviewer  │   │   Evaluator   │   │   Director    │
│               │   │               │   │               │
│ • Talks to    │   │ • Scores      │   │ • Time limits │
│   candidate   │   │   responses   │   │ • Turn limits │
│ • Reveals     │   │ • Sets level  │   │ • Ends session│
│   data when   │   │ • Guides      │   │               │
│   earned      │   │   behavior    │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## The 5-Level Assessment Framework

Candidates are assessed on a 5-level scale. This is the core calibration mechanism:

| Level | Name | Key Indicator | Interviewer Action |
|-------|------|---------------|-------------------|
| 1 | FAIL | No structure, jumps to solutions | DO_NOT_HELP |
| 2 | WEAK | Basic structure, no insight | MINIMAL_HELP |
| 3 | GOOD_NOT_ENOUGH | Solid foundation, lacks depth | LIGHT_HELP (execution only) |
| 4 | CLEAR_PASS | Strong, structured, commercial awareness | CHALLENGE |
| 5 | OUTSTANDING | Excellent, insightful, actionable | LET_SHINE |

### Critical Calibration Rule: Non-Rescuing

**Level 1-2 candidates are NOT helped.** If a candidate cannot structure after the opening, that IS the assessment. The system does not coach weak candidates to better performance.

- Level 1-2: No help - let them struggle, that's the signal
- Level 3+: Help only on **execution** (math errors, data clarification), never on **thinking**

## Agent Calibration Points

### Evaluator Agent (`agents/evaluator.py`)

The hidden brain that determines candidate level.

**Calibration levers:**
- `temperature: 0.3` - Balanced scoring (not too rigid, not too random)
- Runs every 3 candidate responses for periodic calibration
- References case-specific rubrics in JSON files
- Outputs structured JSON with level, justification, and guidance

**What it tracks:**
- `current_level` (1-5)
- `red_flags` - Concerning patterns (no structure, jumps to solutions, bad math)
- `green_flags` - Positive signals (clear framing, hypothesis-driven, quantifies)
- `level_history` - Audit trail of assessments over time

### Interviewer Agent (`agents/interviewer.py`)

The candidate-facing conversation partner.

**Calibration levers:**
- `temperature: 0.3` - Natural but consistent
- Behavior adapts based on current level from evaluator
- Data revelation requires candidate to "earn" it

**Data Revelation Logic:**
Candidates must earn data by:
1. Stating a hypothesis ("I think costs are driving margin compression")
2. Specifying what data they need ("Can I see the cost breakdown?")
3. Explaining why it matters ("To identify which cost category is the driver")

❌ "Can I see the costs?" - Too vague, not earned
✅ "I hypothesize labour costs are driving margin compression because they're variable - can I see the labour cost trend?" - Earned

### Director Agent (`agents/director.py`)

Session constraint manager.

**Calibration levers:**
- `MAX_DURATION_MINUTES = 30`
- `MAX_EXCHANGES = 15` (candidate responses)
- `MIN_AREAS_TO_COVER = 3` (before synthesis allowed)

## Case Configuration Files

Cases are defined in JSON files under `cases/`. Each case contains:

```
cases/
├── coffee_profitability.json  # Profitability decline case
└── market_entry.json          # Market entry strategy case
```

**Key sections in each case file:**

1. **`candidate_prompt`** - The scenario presented to candidates
2. **`hidden_facts`** - Data revealed only when earned
3. **`exploration_areas`** - Topics the candidate should cover
4. **`rubric`** - Level-specific indicators for each exploration area

### Rubric Structure

Each level (1-5) in the rubric has:
- Specific indicators (what to look for)
- Example responses (calibration anchors)
- Recommended action for interviewer

## File Structure

```
adaptive_interview/
├── main.py                 # CLI entry point
├── state.py                # InterviewState definition
├── graph.py                # InterviewRunner orchestration
├── case_loader.py          # Load case JSON files
├── agents/
│   ├── evaluator.py        # Hidden scoring agent
│   ├── interviewer.py      # Candidate-facing agent
│   └── director.py         # Session constraints
├── prompts/
│   ├── evaluator_prompt.py # Scoring instructions
│   └── interviewer_prompt.py # Conversation style
├── cases/
│   ├── coffee_profitability.json
│   └── market_entry.json
├── api/                    # FastAPI backend for candidate app
│   ├── main.py             # API server entry point
│   └── routes/
│       └── interview.py    # Interview API endpoints
├── candidate-app/          # React candidate interface
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
└── ui/
    └── reviewer_dashboard.py  # Streamlit reviewer/admin interface
```

## Two Interfaces

This system has **two separate interfaces** serving different purposes:

### 1. Candidate App (`candidate-app/`)
**What candidates see during interviews.**

- Clean, professional chat interface
- No visible scoring, flags, or assessment information
- Mobile-responsive design
- Focuses entirely on the conversation

### 2. Reviewer Dashboard (`ui/reviewer_dashboard.py`)
**Internal tool for reviewing assessments and debugging.**

- Shows real-time assessment levels (1-5)
- Displays red/green flags as they accumulate
- Shows evaluator guidance and actions
- Debug information and level history
- Token usage tracking

## Running the System

### Option 1: Candidate App (React + FastAPI)

For candidate-facing interviews with the clean React interface:

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

For reviewing assessments and debugging:

```bash
streamlit run ui/reviewer_dashboard.py
```

Open http://localhost:8501 for the reviewer dashboard.

### Option 3: CLI Mode

For development and testing:

```bash
python main.py                    # Interactive case selection
python main.py coffee_profitability  # Run specific case
python main.py --list             # List available cases
```

**Debug commands during interview:**
- `debug` - Show current state
- `scores` - Show assessment history
- `quit` - End early

## What We're Trying to Achieve

### Primary Goal
Build a system that can reliably distinguish between candidate skill levels through adaptive, conversational assessment.

### Key Behaviors to Calibrate

1. **Level Detection Accuracy**
   - Strong candidates should reach Level 4-5
   - Weak candidates should stay at Level 1-2
   - The system should not artificially inflate scores through excessive help

2. **Natural Conversation Flow**
   - Responses should feel human, not robotic
   - Questions should follow logically from candidate answers
   - Silences are okay - don't fill them artificially

3. **Fair Data Revelation**
   - All candidates have access to same hidden facts
   - But they must demonstrate thinking to unlock them
   - Tests research quality, not just asking for everything

4. **Consistent Scoring**
   - Same quality response should get same score across runs
   - Evidence accumulates over time - one bad answer doesn't tank everything
   - Level history provides audit trail

### Success Metrics

- **Scoring consistency**: ±1 level variance for same-quality responses
- **Adaptive behavior**: Clear differentiation between strong/weak candidates
- **Conversation quality**: Natural flow, appropriate pacing
- **Assessment validity**: Levels correlate with actual candidate capability

## Calibration Workflow

When tuning the system:

1. **Adjust Rubrics** (`cases/*.json`)
   - Add/modify level indicators
   - Update example responses for calibration anchors

2. **Tune Evaluator Prompt** (`prompts/evaluator_prompt.py`)
   - Adjust scoring guidance
   - Modify help thresholds

3. **Tune Interviewer Prompt** (`prompts/interviewer_prompt.py`)
   - Adjust conversation style
   - Modify data revelation rules

4. **Adjust Agent Parameters**
   - Temperature settings in agent files
   - Evaluation frequency in `graph.py`
   - Session limits in `director.py`

5. **Test with Synthetic Candidates** (`tests/test_synthetic_candidates.py`)
   - Run strong/weak personas through system
   - Verify adaptive behavior works as expected

## Dependencies

### Python (Backend)
- `langgraph>=0.2.0` - Agent graph orchestration
- `langchain-anthropic>=0.2.0` - Claude LLM integration
- `fastapi>=0.109.0` - API server for candidate app
- `uvicorn>=0.27.0` - ASGI server
- `streamlit>=1.38.0` - Reviewer dashboard
- Claude Sonnet 4 (`claude-sonnet-4-20250514`) - Both agents

### Node.js (Candidate App)
- React 18
- Vite 5
- Tailwind CSS 3

## Environment Setup

```bash
# Create .env file
ANTHROPIC_API_KEY=your_key_here

# Install Python dependencies
pip install fastapi uvicorn

# Install React dependencies
cd candidate-app
npm install
```
