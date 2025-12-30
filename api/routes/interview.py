"""
Interview API routes.
Wraps the existing InterviewRunner for the candidate-facing React app.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from case_loader import initialize_interview_state, get_available_cases
from graph import InterviewRunner

router = APIRouter(prefix="/api", tags=["interview"])

# In-memory session storage (use Redis/DB in production)
sessions: Dict[str, InterviewRunner] = {}


class StartInterviewRequest(BaseModel):
    case_id: str


class StartInterviewResponse(BaseModel):
    session_id: str
    opening_message: str
    case_title: str


class RespondRequest(BaseModel):
    message: str


class RespondResponse(BaseModel):
    interviewer_message: str
    is_complete: bool


class InterviewStatus(BaseModel):
    is_complete: bool
    message_count: int


class CaseInfo(BaseModel):
    id: str
    name: str


@router.get("/cases", response_model=list[CaseInfo])
async def list_cases():
    """List all available cases."""
    cases = get_available_cases()
    return [
        CaseInfo(id=case, name=case.replace("_", " ").title())
        for case in cases
    ]


@router.post("/interviews", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """Start a new interview session."""
    available_cases = get_available_cases()

    if request.case_id not in available_cases:
        raise HTTPException(status_code=404, detail=f"Case '{request.case_id}' not found")

    # Initialize the interview
    state = initialize_interview_state(request.case_id)
    runner = InterviewRunner(state)

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Start the interview and get opening message
    opening = runner.start()

    # Store the session
    sessions[session_id] = runner

    return StartInterviewResponse(
        session_id=session_id,
        opening_message=opening,
        case_title=state["case_title"]
    )


@router.post("/interviews/{session_id}/respond", response_model=RespondResponse)
async def respond_to_interview(session_id: str, request: RespondRequest):
    """Send a candidate message and get the interviewer's response."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    runner = sessions[session_id]

    if runner.is_complete():
        raise HTTPException(status_code=400, detail="Interview is already complete")

    # Get the interviewer's response
    response = runner.respond(request.message)

    return RespondResponse(
        interviewer_message=response,
        is_complete=runner.is_complete()
    )


@router.get("/interviews/{session_id}/status", response_model=InterviewStatus)
async def get_interview_status(session_id: str):
    """Check the status of an interview session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    runner = sessions[session_id]
    messages = runner.get_messages()
    candidate_messages = [m for m in messages if m["role"] == "candidate"]

    return InterviewStatus(
        is_complete=runner.is_complete(),
        message_count=len(candidate_messages)
    )
