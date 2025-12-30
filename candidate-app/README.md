# Candidate Interview App

A clean, professional React interface for candidates taking case interviews.

## Setup

1. Install dependencies:
```bash
cd candidate-app
npm install
```

2. Start the API server (from project root):
```bash
uvicorn api.main:app --reload --port 8000
```

3. Start the React dev server:
```bash
npm run dev
```

4. Open http://localhost:5173 in your browser

## Features

- Clean chat interface focused on the conversation
- Case selection screen
- Typing indicators during AI response
- Mobile-responsive design
- No visible scoring or assessment information

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- Inter font family
