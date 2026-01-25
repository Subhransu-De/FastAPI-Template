.PHONY: help lint run format install docker-up docker-down

help:
	@echo "Available targets:"
	@echo "  make install     - Install dependencies (uv sync)"
	@echo "  make lint        - Run ruff and ty checks"
	@echo "  make format      - Auto-fix linting issues with ruff"
	@echo "  make run         - Start FastAPI dev server with hot reload"
	@echo "  make docker-up   - Start PostgreSQL + FastAPI containers"
	@echo "  make docker-down - Stop containers"

install:
	uv sync --group lint

lint:
	uv run ruff check .
	uv run ty check

format:
	uv run ruff check --fix .

run:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
	    echo "Fill in the .env file"
	fi
	uv run --env-file .env python -m app.main

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
