# Backend

FastAPI + Celery backend for Cursor for 2D Animation.

## Run locally

1. Create env:
   - `cp .env.example .env`
2. Install:
   - `pip install -r requirements-dev.txt`
3. Start API:
   - `uvicorn app.main:app --reload --port 8000`
4. Start worker:
   - `celery -A app.workers.celery_app.celery_app worker -l info -Q preview,export,default`

## Tests

- `pytest -q`

