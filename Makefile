.PHONY: help lint run format install install-prod upgrade docker-up docker-down test test-unit test-integration test-cov

help:
	@echo "Available targets:"
	@echo "  make install                   - Install all dependencies for development"
	@echo "  make install-prod              - Install all dependencies for production"
	@echo "  make upgrade                   - Upgrade all dependencies"
	@echo "  make lint                      - Run ruff and ty checks"
	@echo "  make format                    - Auto-fix linting issues with ruff"
	@echo "  make run                       - Start FastAPI dev server with hot reload"
	@echo "  make docker-up                 - Start full project locally"
	@echo "  make docker-down               - Stop full project locally"
	@echo "  make docker-down-destroy       - Stop full project locally and destroy volumes"
	@echo "  make test                      - Run all tests"
	@echo "  make test-unit                 - Run unit tests only"
	@echo "  make test-cov                  - Run tests with coverage report"

install:
	uv sync --group lint --group test

install-prod:
	uv sync

upgrade:
	uv sync --group lint --group test -U

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

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -m unit

test-integration:
	uv run pytest tests/integration -m integration

test-cov:
	uv run pytest --cov=app --cov-report=term-missing
