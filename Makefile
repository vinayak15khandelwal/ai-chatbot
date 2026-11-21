.PHONY: up down logs test build

up: ## Build and start the whole stack (frontend :3000, backend :8000)
	@test -f .env || (echo "Missing .env - run: cp .env.example .env  (then add your API keys)"; exit 1)
	docker compose up --build -d
	@echo "Frontend: http://localhost:3000   Backend: http://localhost:8000/health"

down: ## Stop the stack (the named volume with the SQLite DB is kept)
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

test: ## Run backend tests locally (needs: cd backend && pip install -r requirements-dev.txt)
	cd backend && python -m pytest -q
