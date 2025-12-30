"""
FastAPI application for the Adaptive Case Interview System.
Provides API endpoints for the candidate-facing React app.

Run with: uvicorn api.main:app --reload --port 8000
"""
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.interview import router as interview_router

app = FastAPI(
    title="Case Interview API",
    description="API for the candidate-facing interview interface",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(interview_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Case Interview API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
