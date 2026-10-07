.PHONY: setup-server setup-client lint test build up down
PY=server/.venv/bin

setup-server:
	python3 -m venv server/.venv
	$(PY)/python -m pip install -e "server[dev]"

setup-client:
	cd client && npm ci

lint:
	cd server && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app
	cd client && npm run lint && npm run typecheck

test:
	cd server && .venv/bin/python -m pytest -q
	cd client && npm test

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down
