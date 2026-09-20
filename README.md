# AI Text Editor

Local AI-powered text editor (RU/EN). Uses [Polza AI](https://polza.ai) (same provider as the calendar agent).

## Features

- Rich text editor with selection-based AI edits
- Quick commands (grammar, shorten, professional tone, translate, etc.) + custom instructions
- Diff preview, accept/reject, version history
- Document memory and personal style profile (from accepted edits)
- Quality metrics before/after (readability heuristics)
- Fact-check flags (claims to verify; no auto-editing facts)
- Import: TXT, Markdown, DOCX, PDF

## Prerequisites

1. **Polza AI** — `POLZA_AI_API_KEY` in `backend/.env`
2. **Python 3.9+** — backend (3.10+ recommended)
3. **Node.js 20+** — frontend dev server

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dev server proxies `/api` to the backend.

## Configuration

In the app **Settings** panel (gear icon):

- Polza base URL and model (`POLZA_AI_*` in `backend/.env`)
- UI language: Russian / English

Data is stored in `backend/data/editor.db` (SQLite).

## Project layout

```
backend/     FastAPI, agents, SQLite, file import
frontend/    React, TipTap, i18n, diff UI
```

## Optional: desktop (Tauri)

A Tauri wrapper can be added later to bundle the web UI; the core app is designed as a local web stack first.
