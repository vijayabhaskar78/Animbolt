#!/bin/bash
set -e

# Start Celery worker in background
celery -A app.workers.celery_app worker --loglevel=info -Q preview,export,default --concurrency=1 &

# Start FastAPI in foreground (keeps container alive)
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
