# Adaptive Case Interview System - Implementation Guide

## Project Overview

Build an AI-powered candidate screening system that conducts case study interviews similar to management consulting firms. The system asks sequential questions, evaluates each response against specific rubrics, and adapts difficulty based on performance.

### Key Principles

1. **Sequential, not holistic**: Each question is scored independently against a narrow rubric
2. **Adaptive difficulty**: Strong candidates get harder follow-ups; struggling candidates get hints
3. **Separation of concerns**: Evaluator (hidden brain) and Interviewer (candidate-facing persona) are separate agents
4. **Transparent scoring**: Every score has explicit reasoning tied to rubric criteria

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      InterviewState                         │
│  (Shared state object passed between all nodes)             │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Interviewer  │    │   Evaluator   │    │   Director    │
│    Agent      │    │    Agent      │    │    Agent      │
│               │    │               │    │               │
│ • Asks Qs     │    │ • Scores      │    │ • Tracks time │
│ • Gives hints │    │ • Adapts      │    │ • Ends session│
│ • Persona     │    │ • Hidden      │    │ • Summarizes  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Flow Per Turn

1. **Interviewer** asks a question (or responds to candidate)
2. **Candidate** provides response
3. **Evaluator** scores response, decides next action
4. **Director** checks if interview should continue
5. **Interviewer** receives directive, generates next message
6. Loop until Director ends session

---

## File Structure

Create this directory structure:

```
adaptive_interview/
├── main.py                 # Entry point
├── state.py                # InterviewState definition
├── graph.py                # LangGraph construction
├── case_loader.py          # Load and validate case files
├── agents/
│   ├── __init__.py
│   ├── evaluator.py        # Scoring and adaptation logic
│   ├── interviewer.py      # Candidate-facing conversation
│   └── director.py         # Session management
├── prompts/
│   ├── __init__.py
│   ├── evaluator_prompt.py
│   └── interviewer_prompt.py
├── cases/
│   ├── coffee_profitability.json
│   └── market_entry.json
├── ui/
│   └── streamlit_app.py    # Web interface
├── tests/
│   └── test_synthetic_candidates.py
├── requirements.txt
└── .env.example
```

---

## Implementation Details

### 1. State Definition (state.py)

```python
from typing import TypedDict, List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum

class Phase(str, Enum):
    INTRO = "INTRO"
    STRUCTURING = "STRUCTURING"
    ANALYSIS = "ANALYSIS"
    CALCULATION = "CALCULATION"
    SYNTHESIS = "SYNTHESIS"
    COMPLETE = "COMPLETE"

class Directive(str, Enum):
    PROVIDE_HINT = "PROVIDE_HINT"
    PROCEED_STANDARD = "PROCEED_STANDARD"
    ADD_COMPLEXITY = "ADD_COMPLEXITY"
    REPEAT_SIMPLIFIED = "REPEAT_SIMPLIFIED"
    MOVE_TO_NEXT_PHASE = "MOVE_TO_NEXT_PHASE"
    END_INTERVIEW = "END_INTERVIEW"

class Message(TypedDict):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    timestamp: str

class QuestionScore(TypedDict):
    question_id: str
    phase: str
    score: int  # 1-5
    reasoning: str
    key_elements_detected: List[str]
    difficulty_at_time: int

class EvaluatorOutput(TypedDict):
    score: int
    reasoning: str
    key_elements_detected: List[str]
    directive: str
    hint_if_needed: Optional[str]
    complexity_addition: Optional[str]
    data_to_reveal: Optional[str]

class InterviewState(TypedDict):
    # Session metadata
    session_id: str
    candidate_id: Optional[str]
    case_id: str
    started_at: str
    
    # Case content (loaded from JSON)
    case_title: str
    case_prompt: str
    hidden_facts: dict
    question_sequence: List[dict]
    
    # Current position
    current_phase: str
    current_question_index: int
    difficulty_level: int  # 1-5
    
    # Conversation
    messages: List[Message]
    
    # Scoring
    question_scores: List[QuestionScore]
    
    # Agent communication
    last_evaluator_output: Optional[EvaluatorOutput]
    next_directive: Optional[str]
    pending_hint: Optional[str]
    pending_complexity: Optional[str]
    pending_data_reveal: Optional[str]
    
    # Control
    is_complete: bool
    final_score: Optional[float]
    final_summary: Optional[str]
```

---

### 2. Case Loader (case_loader.py)

```python
import json
from pathlib import Path
from typing import Dict, Any
from state import InterviewState
import uuid
from datetime import datetime

CASES_DIR = Path(__file__).parent / "cases"

def load_case(case_id: str) -> Dict[str, Any]:
    """Load a case definition from JSON file."""
    case_path = CASES_DIR / f"{case_id}.json"
    if not case_path.exists():
        raise FileNotFoundError(f"Case not found: {case_id}")
    
    with open(case_path, 'r') as f:
        return json.load(f)

def initialize_interview_state(case_id: str, candidate_id: str = None) -> InterviewState:
    """Create a fresh interview state from a case definition."""
    case = load_case(case_id)
    
    return InterviewState(
        session_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        case_id=case_id,
        started_at=datetime.utcnow().isoformat(),
        
        case_title=case["title"],
        case_prompt=case["candidate_prompt"],
        hidden_facts=case["hidden_facts"],
        question_sequence=case["question_sequence"],
        
        current_phase="INTRO",
        current_question_index=0,
        difficulty_level=3,  # Start at medium
        
        messages=[],
        question_scores=[],
        
        last_evaluator_output=None,
        next_directive=None,
        pending_hint=None,
        pending_complexity=None,
        pending_data_reveal=None,
        
        is_complete=False,
        final_score=None,
        final_summary=None
    )

def get_current_question(state: InterviewState) -> dict:
    """Get the current question from the sequence."""
    idx = state["current_question_index"]
    if idx >= len(state["question_sequence"]):
        return None
    return state["question_sequence"][idx]

def get_available_cases() -> List[str]:
    """List all available case IDs."""
    return [f.stem for f in CASES_DIR.glob("*.json")]
```

---

### 3. Evaluator Agent (agents/evaluator.py)

```python
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
import json

from state import InterviewState, EvaluatorOutput, QuestionScore, Directive
from case_loader import get_current_question
from prompts.evaluator_prompt import get_evaluator_system_prompt

# Initialize LLM (use Claude for evaluation - more reliable structured output)
evaluator_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.1,  # Low temperature for consistent scoring
    max_tokens=1024
)

def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluate the candidate's last response and determine next action.
    This agent is HIDDEN from the candidate.
    """
    # Get the last candidate message
    candidate_messages = [m for m in state["messages"] if m["role"] == "candidate"]
    if not candidate_messages:
        # No response yet, just starting
        return {"next_directive": Directive.PROCEED_STANDARD.value}
    
    last_response = candidate_messages[-1]["content"]
    current_question = get_current_question(state)
    
    if current_question is None:
        # No more questions
        return {
            "next_directive": Directive.END_INTERVIEW.value,
            "is_complete": True
        }
    
    # Build the evaluation prompt
    system_prompt = get_evaluator_system_prompt()
    
    evaluation_context = f"""
## Current Phase
{state["current_phase"]}

## Current Difficulty Level
{state["difficulty_level"]} / 5

## Question Asked
{current_question.get("prompt", "Initial case presentation")}

## Rubric for This Question
{json.dumps(current_question.get("rubric", {}), indent=2)}

## Key Elements to Detect
{json.dumps(current_question.get("key_elements", []), indent=2)}

## Hidden Case Facts (for reference)
{json.dumps(state["hidden_facts"], indent=2)}

## Candidate's Response
{last_response}

## Previous Scores in This Interview
{json.dumps(state["question_scores"][-3:], indent=2) if state["question_scores"] else "None yet"}
"""
    
    # Call the LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=evaluation_context)
    ]
    
    response = evaluator_llm.invoke(messages)
    
    # Parse the JSON response
    try:
        # Extract JSON from response (handle markdown code blocks)
        response_text = response.content
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        evaluation = json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Fallback if parsing fails
        evaluation = {
            "score": 3,
            "reasoning": "Could not parse evaluation, defaulting to average",
            "key_elements_detected": [],
            "directive": Directive.PROCEED_STANDARD.value,
            "hint_if_needed": None,
            "complexity_addition": None,
            "data_to_reveal": None
        }
    
    # Record the score
    new_score = QuestionScore(
        question_id=f"q_{state['current_question_index']}",
        phase=state["current_phase"],
        score=evaluation.get("score", 3),
        reasoning=evaluation.get("reasoning", ""),
        key_elements_detected=evaluation.get("key_elements_detected", []),
        difficulty_at_time=state["difficulty_level"]
    )
    
    # Calculate new difficulty level
    score = evaluation.get("score", 3)
    current_diff = state["difficulty_level"]
    
    if score >= 4:
        new_difficulty = min(5, current_diff + 1)
    elif score <= 2:
        new_difficulty = max(1, current_diff - 1)
    else:
        new_difficulty = current_diff
    
    # Determine if we should move to next question
    directive = evaluation.get("directive", Directive.PROCEED_STANDARD.value)
    next_question_index = state["current_question_index"]
    next_phase = state["current_phase"]
    
    if directive in [Directive.PROCEED_STANDARD.value, Directive.ADD_COMPLEXITY.value, Directive.MOVE_TO_NEXT_PHASE.value]:
        next_question_index += 1
        # Check if next question exists and update phase
        if next_question_index < len(state["question_sequence"]):
            next_phase = state["question_sequence"][next_question_index].get("phase", next_phase)
    
    return {
        "question_scores": state["question_scores"] + [new_score],
        "difficulty_level": new_difficulty,
        "current_question_index": next_question_index,
        "current_phase": next_phase,
        "last_evaluator_output": evaluation,
        "next_directive": directive,
        "pending_hint": evaluation.get("hint_if_needed"),
        "pending_complexity": evaluation.get("complexity_addition"),
        "pending_data_reveal": evaluation.get("data_to_reveal")
    }
```

---

### 4. Evaluator Prompt (prompts/evaluator_prompt.py)

```python
def get_evaluator_system_prompt() -> str:
    return """You are an Expert Interview Evaluator for case study interviews. You are HIDDEN from the candidate - they never see your analysis. Your job is to objectively score responses and direct the Interviewer agent.

## Your Responsibilities

1. **Score the Response**: Use the provided rubric to assign a score from 1-5
2. **Identify Key Elements**: Note which expected elements the candidate mentioned
3. **Determine Next Action**: Based on the score, decide what the Interviewer should do
4. **Provide Supporting Content**: If hints or complexity additions are needed, write them

## Scoring Guidelines

- **Score 1**: Completely off-track, fundamental misunderstanding, or no meaningful content
- **Score 2**: Partially relevant but missing critical elements, significant gaps in logic
- **Score 3**: Adequate response covering basics, standard/generic approach, room for depth
- **Score 4**: Strong response with good structure, demonstrates clear thinking, minor gaps only
- **Score 5**: Excellent response, insightful, well-structured, addresses nuances, consultant-quality

## Directive Logic

Based on the score, set the directive:

- **Score 1-2** → `PROVIDE_HINT`: Candidate is stuck. Provide a subtle hint to guide them.
- **Score 3** → `PROCEED_STANDARD`: Adequate. Move to next question normally.
- **Score 4-5** → `ADD_COMPLEXITY`: Candidate is strong. Add a twist or constraint before moving on.
- **Any score + incomplete answer** → `REPEAT_SIMPLIFIED`: Rephrase the question more simply.
- **Final question complete** → `MOVE_TO_NEXT_PHASE` or `END_INTERVIEW`

## Important Rules

1. Grade on LOGIC and CONTENT, not grammar or eloquence (unless communication is being tested)
2. Be consistent - same quality response should get same score across candidates
3. Reference the specific rubric provided, not your general expectations
4. If candidate asks a clarifying question, that's not a scoreable response - directive should be to answer their question
5. Hints should be SUBTLE - don't give away the answer

## Output Format

You MUST respond with valid JSON only, no other text:

```json
{
    "score": <int 1-5>,
    "reasoning": "<2-3 sentences explaining the score based on rubric>",
    "key_elements_detected": ["<element1>", "<element2>"],
    "directive": "<PROVIDE_HINT|PROCEED_STANDARD|ADD_COMPLEXITY|REPEAT_SIMPLIFIED|MOVE_TO_NEXT_PHASE|END_INTERVIEW>",
    "hint_if_needed": "<subtle hint if directive is PROVIDE_HINT, else null>",
    "complexity_addition": "<twist to add if directive is ADD_COMPLEXITY, else null>",
    "data_to_reveal": "<case data to share if candidate asked for it, else null>"
}
```"""
```

---

### 5. Interviewer Agent (agents/interviewer.py)

```python
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from datetime import datetime

from state import InterviewState, Message, Directive
from case_loader import get_current_question
from prompts.interviewer_prompt import get_interviewer_system_prompt

# Initialize LLM (slightly higher temperature for natural conversation)
interviewer_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,
    max_tokens=512
)

def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate the interviewer's response to the candidate.
    This is the ONLY agent the candidate interacts with.
    """
    current_question = get_current_question(state)
    directive = state.get("next_directive", Directive.PROCEED_STANDARD.value)
    
    # Check if interview is complete
    if state.get("is_complete") or current_question is None:
        return generate_closing_message(state)
    
    # Check if this is the very first message
    if not state["messages"]:
        return generate_opening_message(state)
    
    # Build context for the interviewer
    system_prompt = get_interviewer_system_prompt()
    
    # Get recent conversation for context (last 6 messages)
    recent_messages = state["messages"][-6:]
    conversation_history = "\n".join([
        f"{'Interviewer' if m['role'] == 'interviewer' else 'Candidate'}: {m['content']}"
        for m in recent_messages
    ])
    
    context = f"""
## Case Title
{state["case_title"]}

## Current Phase
{state["current_phase"]}

## Recent Conversation
{conversation_history}

## Directive from Evaluator
{directive}

## Current Question to Ask (if moving forward)
{current_question.get("prompt", "")}

## Hint to Provide (if directive is PROVIDE_HINT)
{state.get("pending_hint", "None")}

## Complexity to Add (if directive is ADD_COMPLEXITY)  
{state.get("pending_complexity", "None")}

## Data to Reveal (if candidate asked for information)
{state.get("pending_data_reveal", "None")}

## Hidden Facts (DO NOT reveal unless candidate specifically asks)
{list(state["hidden_facts"].keys())}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]
    
    response = interviewer_llm.invoke(messages)
    
    new_message = Message(
        role="interviewer",
        content=response.content,
        timestamp=datetime.utcnow().isoformat()
    )
    
    # Clear the pending directives after using them
    return {
        "messages": state["messages"] + [new_message],
        "pending_hint": None,
        "pending_complexity": None,
        "pending_data_reveal": None
    }

def generate_opening_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the initial case presentation."""
    opening = f"""Welcome! I'm excited to work through a case with you today.

Let me set the scene: {state["case_prompt"]}

Before we dive in, take a moment to think about how you'd approach this. What would be your initial framework for analyzing this problem?"""
    
    new_message = Message(
        role="interviewer",
        content=opening,
        timestamp=datetime.utcnow().isoformat()
    )
    
    return {
        "messages": [new_message],
        "current_phase": "STRUCTURING"
    }

def generate_closing_message(state: InterviewState) -> Dict[str, Any]:
    """Generate the interview closing."""
    # Calculate final score
    scores = [qs["score"] for qs in state["question_scores"]]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    closing = f"""Excellent, that's a good place to wrap up. You've worked through the key elements of this case well.

Thank you for your time today. We'll be in touch with next steps soon."""
    
    new_message = Message(
        role="interviewer",
        content=closing,
        timestamp=datetime.utcnow().isoformat()
    )
    
    return {
        "messages": state["messages"] + [new_message],
        "is_complete": True,
        "final_score": round(avg_score, 2),
        "current_phase": "COMPLETE"
    }
```

---

### 6. Interviewer Prompt (prompts/interviewer_prompt.py)

```python
def get_interviewer_system_prompt() -> str:
    return """You are a Senior Engagement Manager at a top management consulting firm conducting a case interview. Your persona is professional, encouraging, but rigorous.

## Your Character

- Warm but businesslike
- You value structured thinking and precision
- You give credit where due but push for more
- You never give away answers for free
- You speak concisely (2-4 sentences typically)

## Rules

1. **NEVER** mention scores, difficulty levels, evaluators, or the system
2. **NEVER** invent case facts - only reveal data from the hidden facts when asked
3. **NEVER** tell the candidate if they're doing well or poorly explicitly
4. **ALWAYS** stay in character as a consultant interviewer
5. **ALWAYS** ask only ONE question at a time

## How to Handle Directives

### PROVIDE_HINT
Be subtle. Don't give away the answer. Examples:
- "That's one angle. What else might be driving this?"
- "Interesting. Have you considered the cost side as well?"
- "Walk me through your logic there - I want to make sure I follow."

### PROCEED_STANDARD
Briefly acknowledge their response and move to the next question:
- "Good, that gives us a starting point. Now let's look at..."
- "That's a reasonable framework. Let's dig into the revenue side first."

### ADD_COMPLEXITY
Acknowledge their strength, then add a twist:
- "Solid analysis. Now, what if I told you the competitor just dropped prices by 15%? How does that change your thinking?"
- "Good math. Let's add a wrinkle - the CEO just told us they can't raise prices. What now?"

### REPEAT_SIMPLIFIED
Rephrase more simply without being condescending:
- "Let me reframe that. In simple terms, profits are down. What are the only two things that could cause that?"

### MOVE_TO_NEXT_PHASE
Transition smoothly:
- "Great, we've got a solid structure. Let's move to the numbers now."

## Output Format

Respond naturally as the interviewer would speak. Keep responses to 2-4 sentences. End with a clear question or prompt for the candidate when appropriate.

Do NOT use markdown formatting, bullet points, or headers. Speak naturally."""
```

---

### 7. Director Agent (agents/director.py)

```python
from typing import Dict, Any
from datetime import datetime

from state import InterviewState

# Maximum interview duration in minutes
MAX_DURATION_MINUTES = 30
# Maximum number of questions
MAX_QUESTIONS = 10

def director_node(state: InterviewState) -> Dict[str, Any]:
    """
    Manages session constraints and decides when to end.
    """
    # Check if already complete
    if state.get("is_complete"):
        return {"should_continue": False}
    
    # Check question limit
    if state["current_question_index"] >= len(state["question_sequence"]):
        return {
            "should_continue": False,
            "is_complete": True
        }
    
    if state["current_question_index"] >= MAX_QUESTIONS:
        return {
            "should_continue": False,
            "is_complete": True
        }
    
    # Check time limit
    started = datetime.fromisoformat(state["started_at"])
    elapsed = (datetime.utcnow() - started).total_seconds() / 60
    
    if elapsed >= MAX_DURATION_MINUTES:
        return {
            "should_continue": False,
            "is_complete": True
        }
    
    return {"should_continue": True}

def should_continue(state: InterviewState) -> str:
    """Conditional edge function for the graph."""
    if state.get("is_complete", False):
        return "end"
    if state.get("should_continue", True) is False:
        return "end"
    return "continue"
```

---

### 8. Graph Construction (graph.py)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import InterviewState
from agents.evaluator import evaluator_node
from agents.interviewer import interviewer_node
from agents.director import director_node, should_continue

def build_interview_graph():
    """Construct the interview state machine."""
    
    # Create the graph
    graph = StateGraph(InterviewState)
    
    # Add nodes
    graph.add_node("interviewer", interviewer_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("director", director_node)
    
    # Define edges
    # After interviewer speaks, we wait for candidate (handled externally)
    # When candidate responds, we go to evaluator
    graph.add_edge("evaluator", "director")
    
    # Director decides whether to continue
    graph.add_conditional_edges(
        "director",
        should_continue,
        {
            "continue": "interviewer",
            "end": END
        }
    )
    
    # Evaluator always goes to director
    graph.add_edge("evaluator", "director")
    
    # Set entry point
    graph.set_entry_point("interviewer")
    
    # Compile with memory for state persistence
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

def create_interview_runner():
    """Create a runner that handles the conversation loop."""
    graph = build_interview_graph()
    
    class InterviewRunner:
        def __init__(self, initial_state: InterviewState):
            self.state = initial_state
            self.thread_id = initial_state["session_id"]
            self.config = {"configurable": {"thread_id": self.thread_id}}
        
        def start(self) -> str:
            """Start the interview and return the opening message."""
            result = graph.invoke(self.state, self.config)
            self.state = result
            return self._get_last_interviewer_message()
        
        def respond(self, candidate_message: str) -> str:
            """Process candidate response and return interviewer's reply."""
            from datetime import datetime
            from state import Message
            
            # Add candidate message to state
            new_message = Message(
                role="candidate",
                content=candidate_message,
                timestamp=datetime.utcnow().isoformat()
            )
            self.state["messages"] = self.state["messages"] + [new_message]
            
            # Run through evaluator -> director -> interviewer
            # First evaluate
            self.state = {**self.state, **evaluator_node(self.state)}
            # Then check director
            self.state = {**self.state, **director_node(self.state)}
            
            if self.state.get("is_complete"):
                # Generate closing
                self.state = {**self.state, **interviewer_node(self.state)}
            else:
                # Generate next question
                self.state = {**self.state, **interviewer_node(self.state)}
            
            return self._get_last_interviewer_message()
        
        def _get_last_interviewer_message(self) -> str:
            """Get the most recent interviewer message."""
            for msg in reversed(self.state["messages"]):
                if msg["role"] == "interviewer":
                    return msg["content"]
            return ""
        
        def get_state(self) -> InterviewState:
            """Get current state (for debugging/admin view)."""
            return self.state
        
        def is_complete(self) -> bool:
            """Check if interview is finished."""
            return self.state.get("is_complete", False)
        
        def get_scores(self) -> list:
            """Get all question scores."""
            return self.state.get("question_scores", [])
    
    return InterviewRunner
```

---

### 9. Main Entry Point (main.py)

```python
from case_loader import initialize_interview_state, get_available_cases
from graph import create_interview_runner

def run_cli_interview():
    """Run an interview in the command line for testing."""
    
    print("=== Adaptive Case Interview System ===\n")
    
    # List available cases
    cases = get_available_cases()
    print("Available cases:")
    for i, case in enumerate(cases, 1):
        print(f"  {i}. {case}")
    
    # Select case
    case_idx = int(input("\nSelect case number: ")) - 1
    case_id = cases[case_idx]
    
    # Initialize
    state = initialize_interview_state(case_id)
    InterviewRunner = create_interview_runner()
    runner = InterviewRunner(state)
    
    # Start interview
    print("\n" + "="*50)
    print("INTERVIEW STARTING")
    print("="*50 + "\n")
    
    opening = runner.start()
    print(f"Interviewer: {opening}\n")
    
    # Conversation loop
    while not runner.is_complete():
        candidate_input = input("You: ").strip()
        if candidate_input.lower() in ["quit", "exit", "q"]:
            break
        
        response = runner.respond(candidate_input)
        print(f"\nInterviewer: {response}\n")
        
        # Debug: show current difficulty (would be hidden in production)
        current_state = runner.get_state()
        print(f"[DEBUG] Difficulty: {current_state['difficulty_level']}/5, Phase: {current_state['current_phase']}")
        print()
    
    # Show final results
    print("\n" + "="*50)
    print("INTERVIEW COMPLETE")
    print("="*50)
    
    final_state = runner.get_state()
    print(f"\nFinal Score: {final_state.get('final_score', 'N/A')}/5")
    print("\nQuestion Scores:")
    for qs in runner.get_scores():
        print(f"  - {qs['phase']}: {qs['score']}/5 - {qs['reasoning'][:50]}...")

if __name__ == "__main__":
    run_cli_interview()
```

---

### 10. Streamlit UI (ui/streamlit_app.py)

```python
import streamlit as st
from datetime import datetime
import sys
sys.path.append("..")

from case_loader import initialize_interview_state, get_available_cases
from graph import create_interview_runner

st.set_page_config(page_title="Case Interview", layout="wide")

# Initialize session state
if "runner" not in st.session_state:
    st.session_state.runner = None
    st.session_state.started = False

# Sidebar for admin/debug
with st.sidebar:
    st.header("Admin Panel")
    
    if st.session_state.runner:
        state = st.session_state.runner.get_state()
        
        st.subheader("Current State")
        st.metric("Difficulty Level", f"{state['difficulty_level']}/5")
        st.metric("Phase", state['current_phase'])
        st.metric("Questions Completed", len(state['question_scores']))
        
        st.subheader("Score History")
        for qs in state['question_scores']:
            with st.expander(f"{qs['phase']} - Score: {qs['score']}/5"):
                st.write(qs['reasoning'])
                st.write(f"Elements detected: {qs['key_elements_detected']}")
        
        if state.get('last_evaluator_output'):
            st.subheader("Last Evaluation")
            st.json(state['last_evaluator_output'])
    
    st.divider()
    if st.button("Reset Interview"):
        st.session_state.runner = None
        st.session_state.started = False
        st.rerun()

# Main content
st.title("Case Interview")

# Case selection
if not st.session_state.started:
    cases = get_available_cases()
    selected_case = st.selectbox("Select a case:", cases)
    
    if st.button("Start Interview"):
        state = initialize_interview_state(selected_case)
        InterviewRunner = create_interview_runner()
        st.session_state.runner = InterviewRunner(state)
        st.session_state.started = True
        
        # Get opening message
        opening = st.session_state.runner.start()
        st.rerun()

# Interview interface
if st.session_state.started and st.session_state.runner:
    runner = st.session_state.runner
    state = runner.get_state()
    
    # Display conversation
    for msg in state["messages"]:
        if msg["role"] == "interviewer":
            with st.chat_message("assistant"):
                st.write(msg["content"])
        elif msg["role"] == "candidate":
            with st.chat_message("user"):
                st.write(msg["content"])
    
    # Check if complete
    if runner.is_complete():
        st.success(f"Interview Complete! Final Score: {state.get('final_score', 'N/A')}/5")
    else:
        # Input for candidate
        if prompt := st.chat_input("Your response..."):
            # Show candidate message immediately
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get interviewer response
            with st.spinner("Thinking..."):
                response = runner.respond(prompt)
            
            with st.chat_message("assistant"):
                st.write(response)
            
            st.rerun()
```

---

### 11. Case Content File (cases/coffee_profitability.json)

```json
{
    "case_id": "coffee_profitability",
    "title": "JavaStop Coffee Chain Profitability",
    "difficulty_baseline": 3,
    "estimated_duration_minutes": 20,
    
    "candidate_prompt": "Your client is JavaStop, a mid-sized coffee chain with 500 stores in the Northeast US. Revenues have been growing steadily at 5% per year, but profits have dropped by 20% in the last 12 months. The CEO wants to know why profits are declining and what to do about it.",
    
    "hidden_facts": {
        "business_model": {
            "revenue_split": {"coffee": 0.70, "food": 0.30},
            "store_count": 500,
            "avg_transaction": 8.50,
            "daily_transactions_per_store": 400
        },
        "revenue_changes": {
            "coffee_volume": "+10%",
            "coffee_price": "0% (no change)",
            "food_volume": "0% (flat)",
            "food_price": "0% (no change)",
            "total_revenue_growth": "+5%"
        },
        "cost_changes": {
            "fixed_costs_rent": "0% (flat)",
            "fixed_costs_labor": "+3% (slight increase)",
            "variable_costs_beans": "+40% (Brazil drought)",
            "variable_costs_cups_packaging": "+15%",
            "variable_costs_food_ingredients": "+5%"
        },
        "market_context": {
            "competitor_starbeans_price_change": "+10% (raised prices)",
            "javastop_price_change": "0% (did not raise)",
            "consumer_price_sensitivity": "moderate",
            "brand_perception": "value-oriented"
        },
        "root_cause": "Variable costs (especially coffee beans) up 40% due to Brazil supply shortage, while prices held flat",
        "key_insight": "Competitor raised prices 10%, JavaStop could follow without major volume loss"
    },
    
    "question_sequence": [
        {
            "id": "q1_structure",
            "phase": "STRUCTURING",
            "prompt": "How would you structure your analysis of this profitability problem?",
            "key_elements": ["revenue", "costs", "profit equation", "breakdown", "segmentation"],
            "rubric": {
                "1": "Random brainstorming with no clear structure. Misses that profit = revenue - costs.",
                "2": "Mentions revenue and costs but no systematic breakdown. Jumps to solutions.",
                "3": "States profit = revenue - costs. Generic breakdown without tailoring to coffee business.",
                "4": "Clear profit framework with revenue drivers (price × volume) AND cost drivers (fixed vs variable). Some segmentation.",
                "5": "Custom framework: Revenue by product (coffee/food), by channel, costs broken into fixed (rent, labor) and variable (beans, packaging). Considers margin by product."
            },
            "hints": {
                "level_1": "Let's start with the basics. What's the formula for profit?",
                "level_2": "Good start. How might you break down the revenue side further?"
            }
        },
        {
            "id": "q2_hypothesis",
            "phase": "STRUCTURING", 
            "prompt": "Given that revenue is UP 5% but profit is DOWN 20%, what does that tell you? Where would you focus first?",
            "key_elements": ["costs increasing", "cost focus", "margin compression", "not a revenue problem"],
            "rubric": {
                "1": "Focuses on revenue despite being told it's growing. Misses the cost implication.",
                "2": "Recognizes costs might be the issue but can't articulate why.",
                "3": "Correctly identifies costs must be rising faster than revenue. Suggests looking at cost breakdown.",
                "4": "Clear logic: if revenue up and profit down, costs must be growing faster. Asks about cost structure.",
                "5": "Quantifies the gap: 5% revenue growth vs 20% profit decline implies significant cost surge. Hypothesizes variable vs fixed costs."
            },
            "hints": {
                "level_1": "If revenue is going up but profit is going down, what must be happening?",
                "level_2": "You're on the right track with costs. What types of costs might a coffee chain have?"
            }
        },
        {
            "id": "q3_data_request",
            "phase": "ANALYSIS",
            "prompt": "Good thinking. What specific data would you want to see to test your hypothesis?",
            "key_elements": ["cost breakdown", "variable costs", "fixed costs", "trends", "per-unit costs"],
            "rubric": {
                "1": "Asks for irrelevant data (customer satisfaction, competitor store count).",
                "2": "Asks for 'costs' but not specific enough to be actionable.",
                "3": "Asks for cost breakdown by category. Reasonable but generic.",
                "4": "Asks for fixed vs variable split, trends over time, and per-unit costs.",
                "5": "Prioritized data request: variable costs by input (beans, packaging), fixed costs (rent, labor), YoY comparison, and cost per cup trend."
            },
            "data_to_reveal": "Here's what we have: Fixed costs (rent, labor) are essentially flat, up only 3%. But variable costs have increased significantly - coffee beans are up 40% due to a drought in Brazil, and packaging is up 15%.",
            "hints": {
                "level_1": "What categories of costs would a coffee shop have?",
                "level_2": "Think about which costs change with volume vs which stay the same."
            }
        },
        {
            "id": "q4_analysis",
            "phase": "ANALYSIS",
            "prompt": "Coffee bean costs are up 40% due to a Brazil drought. Given that coffee is 70% of revenue, what's the impact on overall costs? Walk me through the math.",
            "key_elements": ["percentage calculation", "cost impact", "margin math"],
            "rubric": {
                "1": "Cannot attempt the calculation or gets fundamentally wrong answer.",
                "2": "Starts calculation but makes significant errors or cannot complete.",
                "3": "Attempts calculation with right approach, minor errors in execution.",
                "4": "Correct calculation: 70% of business × 40% cost increase = 28% cost increase on that segment.",
                "5": "Correct calculation plus insight: explains how this flows through to margin, estimates profit impact."
            },
            "hints": {
                "level_1": "Let's simplify. If coffee is 70% of the business and bean costs went up 40%, what's 70% times 40%?",
                "level_2": "You're close. Remember, we're looking for the weighted impact on overall costs."
            }
        },
        {
            "id": "q5_recommendation_setup",
            "phase": "ANALYSIS",
            "prompt": "One more data point: your main competitor, StarBeans, raised their prices by 10% last month. JavaStop held prices flat. What options does that open up?",
            "key_elements": ["price increase", "competitor benchmark", "pricing power", "market positioning"],
            "rubric": {
                "1": "Misses the pricing opportunity entirely. Suggests cutting costs only.",
                "2": "Recognizes competitor raised prices but doesn't connect to JavaStop's opportunity.",
                "3": "Suggests JavaStop could raise prices too, but doesn't quantify or consider risks.",
                "4": "Clear recommendation: JavaStop has room to raise prices (up to 10%) since competitor already did. Considers customer reaction.",
                "5": "Nuanced: Recommends price increase in range (5-8%), acknowledges brand positioning, suggests testing in select markets first."
            },
            "complexity_additions": {
                "strong_candidate": "What if I told you JavaStop has positioned itself as the 'value' alternative to StarBeans? Does that change your recommendation?",
                "very_strong": "The CEO is worried about volume loss. How would you model the break-even point - how much volume can we lose before the price increase backfires?"
            }
        },
        {
            "id": "q6_synthesis",
            "phase": "SYNTHESIS",
            "prompt": "We're running short on time. If you had to walk into the CEO's office right now, what would you tell her? Give me your recommendation in 30 seconds.",
            "key_elements": ["clear recommendation", "reasoning", "risks", "next steps"],
            "rubric": {
                "1": "Rambling, no clear recommendation, or recommendation doesn't follow from analysis.",
                "2": "Has a recommendation but poorly structured, missing key supporting points.",
                "3": "Clear recommendation (raise prices) with basic reasoning. Missing risks or next steps.",
                "4": "Structured response: Recommendation + 2-3 reasons + acknowledgment of risks.",
                "5": "CEO-ready: Crisp recommendation, quantified impact, key risk with mitigation, clear next step. Under 30 seconds equivalent."
            },
            "hints": {
                "level_1": "Structure it as: Here's what I recommend, here's why, here's the risk.",
                "level_2": "Start with the answer. What should the CEO do?"
            }
        }
    ],
    
    "scoring_weights": {
        "STRUCTURING": 0.25,
        "ANALYSIS": 0.50,
        "SYNTHESIS": 0.25
    },
    
    "pass_threshold": 3.0,
    "strong_threshold": 4.0
}
```

---

### 12. Second Case File (cases/market_entry.json)

```json
{
    "case_id": "market_entry",
    "title": "TechFlow Market Entry - Southeast Asia",
    "difficulty_baseline": 3,
    "estimated_duration_minutes": 25,
    
    "candidate_prompt": "Your client is TechFlow, a B2B software company based in the US that sells project management tools to mid-sized companies. They currently have $50M in annual revenue, all from North America. The CEO wants to expand into Southeast Asia and has asked you to advise on whether this is a good idea and how to approach it.",
    
    "hidden_facts": {
        "company_profile": {
            "current_revenue": "$50M",
            "current_markets": "US and Canada only",
            "product": "Cloud-based project management SaaS",
            "target_customer": "Companies with 100-1000 employees",
            "pricing": "$15/user/month",
            "current_growth_rate": "15% YoY",
            "profit_margin": "20%"
        },
        "sea_market_data": {
            "total_addressable_market": "$2B",
            "growth_rate": "25% YoY",
            "key_countries": ["Singapore", "Indonesia", "Vietnam", "Thailand", "Philippines"],
            "competitor_presence": "Low - mostly local players",
            "enterprise_adoption": "Growing rapidly, 5 years behind US"
        },
        "challenges": {
            "localization": "Need local language support (5+ languages)",
            "payment_methods": "Credit card penetration low, need local payment options",
            "data_residency": "Some countries require local data storage",
            "sales_model": "Relationship-based selling, need local presence"
        },
        "opportunities": {
            "first_mover": "No major US competitor has entered yet",
            "partnerships": "Potential to partner with local telcos for distribution",
            "pricing_flexibility": "Could price 30-40% lower and still be profitable"
        },
        "recommended_approach": "Start with Singapore as beachhead, partner with local reseller, then expand",
        "investment_required": "$5-8M over 2 years",
        "expected_payback": "3-4 years"
    },
    
    "question_sequence": [
        {
            "id": "q1_structure",
            "phase": "STRUCTURING",
            "prompt": "How would you think about whether TechFlow should enter Southeast Asia?",
            "key_elements": ["market attractiveness", "competitive position", "feasibility", "fit"],
            "rubric": {
                "1": "No clear framework. Jumps to conclusion without analysis.",
                "2": "Lists some considerations but not organized into coherent structure.",
                "3": "Basic market entry framework: market size, competition, capabilities needed.",
                "4": "Strong framework: Market attractiveness + Company fit + Implementation feasibility.",
                "5": "Comprehensive: Market (size, growth, dynamics) + Competition + Capabilities/Gaps + Financial case + Risks. Prioritizes what to analyze first."
            }
        },
        {
            "id": "q2_market",
            "phase": "ANALYSIS",
            "prompt": "Let's start with market attractiveness. What would you want to know about the Southeast Asian market?",
            "key_elements": ["market size", "growth", "customer segments", "competitive landscape"],
            "rubric": {
                "1": "Generic questions not specific to B2B software or the region.",
                "2": "Asks about market size but misses growth, competition, or customer dynamics.",
                "3": "Asks about TAM, growth rate, and competition. Reasonable coverage.",
                "4": "Asks about TAM by country, segment (SMB vs enterprise), growth drivers, and competitive intensity.",
                "5": "Sophisticated: TAM/SAM/SOM distinction, growth drivers, customer adoption curve, competitive gaps, regulatory environment."
            },
            "data_to_reveal": "The total addressable market is about $2B, growing at 25% per year - faster than North America. Competition is mostly local players; no major US competitor has entered yet."
        },
        {
            "id": "q3_challenges",
            "phase": "ANALYSIS",
            "prompt": "The market looks attractive. What challenges or risks do you see with entering Southeast Asia?",
            "key_elements": ["localization", "go-to-market", "operations", "regulatory"],
            "rubric": {
                "1": "Cannot identify meaningful challenges or lists irrelevant risks.",
                "2": "Identifies 1-2 obvious challenges but misses key operational issues.",
                "3": "Good list: language, payment methods, local presence needed.",
                "4": "Comprehensive: Localization + GTM model + data residency + competitive response + organizational readiness.",
                "5": "Prioritized and specific: Ranks challenges by impact, identifies which are solvable vs structural, suggests how to test assumptions."
            }
        },
        {
            "id": "q4_entry_mode",
            "phase": "ANALYSIS",
            "prompt": "Given these challenges, how would you recommend TechFlow enter the market? What options do they have?",
            "key_elements": ["entry modes", "organic vs partner", "beachhead strategy", "phasing"],
            "rubric": {
                "1": "Only considers one option without evaluating alternatives.",
                "2": "Lists options but cannot articulate pros/cons of each.",
                "3": "Compares 2-3 entry modes (direct, partner, acquisition) with basic trade-offs.",
                "4": "Evaluates options against company capabilities, recommends phased approach starting with one country.",
                "5": "Strategic: Recommends beachhead market with clear criteria, outlines partnership model, phases investment, identifies success metrics."
            },
            "complexity_additions": {
                "strong_candidate": "The CEO is impatient and wants to enter 3 countries simultaneously. How would you push back on that?"
            }
        },
        {
            "id": "q5_synthesis",
            "phase": "SYNTHESIS",
            "prompt": "Summarize your recommendation for the CEO. Should TechFlow enter Southeast Asia, and if so, how?",
            "key_elements": ["clear recommendation", "rationale", "approach", "investment", "risks"],
            "rubric": {
                "1": "No clear recommendation or recommendation contradicts analysis.",
                "2": "Has recommendation but missing key elements (how, when, investment).",
                "3": "Clear yes/no with basic rationale and high-level approach.",
                "4": "Structured: Recommendation + Market rationale + Entry approach + Investment range + Key risks.",
                "5": "Board-ready: Crisp recommendation, quantified opportunity, phased approach with milestones, risk mitigation, clear ask."
            }
        }
    ],
    
    "scoring_weights": {
        "STRUCTURING": 0.20,
        "ANALYSIS": 0.55,
        "SYNTHESIS": 0.25
    },
    
    "pass_threshold": 3.0,
    "strong_threshold": 4.0
}
```

---

### 13. Requirements File (requirements.txt)

```
langgraph>=0.2.0
langchain>=0.3.0
langchain-anthropic>=0.2.0
langchain-openai>=0.2.0
pydantic>=2.0.0
streamlit>=1.38.0
python-dotenv>=1.0.0
```

---

### 14. Environment Example (.env.example)

```
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

---

## Testing Instructions

### Manual Testing (CLI)

```bash
cd adaptive_interview
python main.py
```

### Synthetic Candidate Testing

Create `tests/test_synthetic_candidates.py`:

```python
"""
Run synthetic candidates through the system to validate adaptive behavior.
"""
from langchain_anthropic import ChatAnthropic
import sys
sys.path.append("..")

from case_loader import initialize_interview_state
from graph import create_interview_runner

# Candidate personas
STRONG_CANDIDATE_PROMPT = """You are an excellent consulting candidate with McKinsey experience. 
When asked case questions:
- Always structure your thinking clearly
- Use frameworks like profit = revenue - costs
- Ask smart clarifying questions
- Do mental math accurately
- Give crisp, CEO-ready summaries"""

WEAK_CANDIDATE_PROMPT = """You are a nervous candidate with no consulting experience.
When asked case questions:
- Give rambling, unstructured answers
- Miss obvious points
- Struggle with basic math
- Use lots of filler words
- Never summarize clearly"""

def run_synthetic_interview(candidate_prompt: str, case_id: str = "coffee_profitability"):
    """Run a synthetic candidate through an interview."""
    
    candidate_llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
    
    state = initialize_interview_state(case_id)
    InterviewRunner = create_interview_runner()
    runner = InterviewRunner(state)
    
    # Start
    interviewer_msg = runner.start()
    print(f"Interviewer: {interviewer_msg}\n")
    
    turn = 0
    while not runner.is_complete() and turn < 15:
        # Generate candidate response
        candidate_response = candidate_llm.invoke([
            {"role": "system", "content": candidate_prompt},
            {"role": "user", "content": f"The interviewer said: '{interviewer_msg}'\n\nRespond as the candidate would. Keep response under 150 words."}
        ])
        
        print(f"Candidate: {candidate_response.content}\n")
        
        # Get interviewer response
        interviewer_msg = runner.respond(candidate_response.content)
        print(f"Interviewer: {interviewer_msg}\n")
        
        # Debug info
        state = runner.get_state()
        print(f"[Difficulty: {state['difficulty_level']}, Scores: {[s['score'] for s in state['question_scores']]}]\n")
        
        turn += 1
    
    # Results
    final_state = runner.get_state()
    return {
        "final_score": final_state.get("final_score"),
        "difficulty_progression": [s["difficulty_at_time"] for s in final_state["question_scores"]],
        "scores": [s["score"] for s in final_state["question_scores"]]
    }

if __name__ == "__main__":
    print("="*60)
    print("STRONG CANDIDATE TEST")
    print("="*60)
    strong_result = run_synthetic_interview(STRONG_CANDIDATE_PROMPT)
    print(f"\nStrong Candidate Result: {strong_result}")
    
    print("\n" + "="*60)
    print("WEAK CANDIDATE TEST")  
    print("="*60)
    weak_result = run_synthetic_interview(WEAK_CANDIDATE_PROMPT)
    print(f"\nWeak Candidate Result: {weak_result}")
    
    # Validation
    print("\n" + "="*60)
    print("VALIDATION")
    print("="*60)
    print(f"Strong candidate avg score: {sum(strong_result['scores'])/len(strong_result['scores']):.1f}")
    print(f"Weak candidate avg score: {sum(weak_result['scores'])/len(weak_result['scores']):.1f}")
    print(f"Strong reached max difficulty: {5 in strong_result['difficulty_progression']}")
    print(f"Weak stayed at low difficulty: {max(weak_result['difficulty_progression']) <= 3}")
```

---

## Success Criteria

1. **Scoring Consistency**: Same quality response should get same score (±1) across runs
2. **Adaptive Behavior**: Strong candidates should reach difficulty 4-5; weak should stay at 1-2
3. **Natural Conversation**: Interviewer responses should feel human, not robotic
4. **Hint Effectiveness**: Hints should help struggling candidates without giving away answers
5. **Complexity Scaling**: Strong candidates should get follow-up twists that test deeper thinking

---

## Implementation Order

1. Start with `state.py` - get the data structures right
2. Build `case_loader.py` and create the first case JSON
3. Implement `evaluator.py` with the prompt - this is the core logic
4. Implement `interviewer.py` - focus on natural conversation
5. Wire up `graph.py` with basic flow
6. Build CLI interface in `main.py` for testing
7. Add Streamlit UI
8. Run synthetic candidate tests to validate
9. Iterate on prompts based on test results

---

## Notes for Claude Code

- Use Anthropic's Claude for both evaluator and interviewer (claude-sonnet-4-20250514)
- Set evaluator temperature to 0.1 for consistency
- Set interviewer temperature to 0.3 for natural conversation
- The evaluator MUST output valid JSON - include retry logic if parsing fails
- Store all state in memory for POC; add database persistence later
- The UI should hide all evaluator output from candidates
