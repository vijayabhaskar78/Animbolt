.PHONY: up down logs test-backend

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs --tail=200

test-backend:
	cd backend && pytest -q

