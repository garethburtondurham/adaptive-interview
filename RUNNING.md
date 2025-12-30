# Running the Interview System

This project has three ways to run interviews, plus a reviewer dashboard.

## Prerequisites

1. **Python 3.10+** with pip
2. **Node.js 18+** with npm
3. **Anthropic API Key** in `.env` file:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

## Quick Start

### Install Dependencies (First Time Only)

```bash
# Python dependencies
pip install -r requirements.txt
pip install fastapi uvicorn

# React dependencies
cd candidate-app && npm install && cd ..
```

Or use the Makefile:
```bash
make install
```

---

## Option 1: Candidate App (Recommended for Interviews)

The clean, professional interface that candidates see. No scoring or debug info visible.

**Requires two terminals:**

### Terminal 1 - Start API Server
```bash
uvicorn api.main:app --reload --port 8000
```

### Terminal 2 - Start React App
```bash
cd candidate-app
npm run dev
```

**Open:** http://localhost:5173

Or use the Makefile:
```bash
make candidate    # Starts both servers (API in background)
```

---

## Option 2: Reviewer Dashboard (For Assessment Review)

The Streamlit dashboard showing real-time scoring, flags, and debug info.

```bash
streamlit run ui/reviewer_dashboard.py
```

**Open:** http://localhost:8501

Or use the Makefile:
```bash
make reviewer
```

---

## Option 3: CLI Mode (For Development/Testing)

Text-based interface in the terminal.

```bash
python main.py                      # Interactive case selection
python main.py coffee_profitability # Run specific case
python main.py --list               # List available cases
```

**Debug commands during interview:**
- `debug` - Show current state
- `scores` - Show assessment history
- `quit` - End early

Or use the Makefile:
```bash
make cli
```

---

## Running Both Interfaces Simultaneously

You can run the candidate app AND reviewer dashboard at the same time to see both views:

### Terminal 1 - API Server
```bash
uvicorn api.main:app --reload --port 8000
```

### Terminal 2 - React Candidate App
```bash
cd candidate-app && npm run dev
```

### Terminal 3 - Streamlit Reviewer Dashboard
```bash
streamlit run ui/reviewer_dashboard.py
```

Now you can:
- Use http://localhost:5173 as the candidate
- Watch http://localhost:8501 to see real-time assessment

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make candidate` | Run candidate app (API + React) |
| `make reviewer` | Run reviewer dashboard (Streamlit) |
| `make cli` | Run CLI interview |
| `make api` | Run API server only |
| `make react` | Run React dev server only |
| `make clean` | Kill all running servers |

---

## Ports Used

| Service | Port | URL |
|---------|------|-----|
| FastAPI | 8000 | http://localhost:8000 |
| React (Vite) | 5173 | http://localhost:5173 |
| Streamlit | 8501 | http://localhost:8501 |

---

## Troubleshooting

### "Unable to load cases" in React app
- Make sure the API server is running on port 8000
- Check the terminal running uvicorn for errors

### "ANTHROPIC_API_KEY not set"
- Create a `.env` file in the project root
- Add your API key: `ANTHROPIC_API_KEY=sk-ant-...`

### Port already in use
```bash
# Kill process on specific port (Windows)
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Or use make clean
make clean
```

### React app not connecting to API
- Vite proxies `/api` requests to port 8000
- Make sure API is running before starting React
