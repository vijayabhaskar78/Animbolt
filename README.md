# Cursor for 2D Animation

AI-powered platform that turns text prompts into Manim-based educational animation workflows with:

- Prompt-to-scene generation (Groq -> Manim code)
- Progressive preview job pipeline (FastAPI + Celery + Redis)
- Scene composition and export
- Voiceover upload and TTS (`edge-tts`)

## Stack

- Frontend: Next.js (App Router), TypeScript
- API: FastAPI, SQLAlchemy, JWT auth
- Jobs: Celery + Redis
- Data: PostgreSQL
- Render runtime: ManimGL + ffmpeg (with simulation fallback for local dev)

## Quick Start

1. Copy environment files:
   - `cp .env.example .env`
2. Start services:
   - `docker compose up -d --build`
3. Open:
   - Frontend: `http://localhost:3000`
   - API docs: `http://localhost:8000/docs`

## Project Layout

- `backend/` FastAPI service + Celery worker + tests
- `frontend/` Next.js UI
- `infra/` reverse proxy config
- `scripts/` ops scripts (backup/restore helpers)

## Reliability Notes

- Render job retries with bounded attempts.
- Generated Python is validated via AST policy before execution.
- Queue separation for preview/export.
- Structured logs and health endpoints.

