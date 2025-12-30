.PHONY: install candidate reviewer cli api react clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make candidate  - Run candidate app (API + React)"
	@echo "  make reviewer   - Run reviewer dashboard (Streamlit)"
	@echo "  make cli        - Run CLI interview"
	@echo "  make api        - Run API server only"
	@echo "  make react      - Run React dev server only"
	@echo "  make clean      - Kill all running servers"

# Install all dependencies
install:
	pip install -r requirements.txt
	pip install fastapi uvicorn
	cd candidate-app && npm install

# Run candidate-facing app (starts API in background, then React)
candidate: api-bg react

# Run API server in background
api-bg:
	@echo "Starting API server on http://localhost:8000..."
	start /B uvicorn api.main:app --reload --port 8000

# Run API server (foreground)
api:
	uvicorn api.main:app --reload --port 8000

# Run React dev server
react:
	cd candidate-app && npm run dev

# Run reviewer dashboard
reviewer:
	streamlit run ui/reviewer_dashboard.py

# Run CLI interview
cli:
	python main.py

# Kill all running servers (Windows)
clean:
	@echo "Stopping servers..."
	-taskkill /F /IM uvicorn.exe 2>nul
	-taskkill /F /IM node.exe 2>nul
	-taskkill /F /IM streamlit.exe 2>nul
	@echo "Done."

# Development: run API and React in separate windows
dev:
	@echo "Starting API server..."
	start cmd /k "uvicorn api.main:app --reload --port 8000"
	@echo "Starting React app..."
	start cmd /k "cd candidate-app && npm run dev"
	@echo ""
	@echo "API:       http://localhost:8000"
	@echo "Candidate: http://localhost:5173"

# Run everything (API, React, Streamlit)
all:
	start cmd /k "uvicorn api.main:app --reload --port 8000"
	start cmd /k "cd candidate-app && npm run dev"
	start cmd /k "streamlit run ui/reviewer_dashboard.py"
	@echo ""
	@echo "API:       http://localhost:8000"
	@echo "Candidate: http://localhost:5173"
	@echo "Reviewer:  http://localhost:8501"
