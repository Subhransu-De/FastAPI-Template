.PHONY: help lint lint-ruff lint-ty lint-imports run format install install-prod upgrade docker-up docker-down docker-down-destroy test test-unit test-cov

help:
	@echo "Available targets:"
	@echo "  make install                   - Install all dependencies for development"
	@echo "  make install-prod              - Install all dependencies for production"
	@echo "  make upgrade                   - Upgrade all dependencies"
	@echo "  make lint                      - Run ruff, ty, and import-linter checks"
	@echo "  make lint-imports              - Run import-linter architecture checks"
	@echo "  make format                    - Auto-fix linting issues with ruff"
	@echo "  make run                       - Start FastAPI dev server with hot reload"
	@echo "  make docker-up                 - Start full project locally"
	@echo "  make docker-down               - Stop full project locally"
	@echo "  make docker-down-destroy       - Stop full project locally and destroy volumes"
	@echo "  make test                      - Run all tests"
	@echo "  make test-unit                 - Run unit tests only"
	@echo "  make test-cov                  - Run tests with coverage report"

install:
	uv sync --group lint --group test --all-packages

install-prod:
	uv sync

upgrade:
	uv sync --group lint --group test --all-packages -U

lint: lint-ruff lint-ty lint-imports

lint-ruff:
	uv run --group lint --all-packages ruff check app tests alembic scenario-tests

lint-ty:
	uv run --group lint --all-packages ty check app tests alembic scenario-tests

lint-imports:
	uv run --group lint --all-packages lint-imports --config .importlinter

format:
	uv run --group lint --all-packages ruff check --fix app tests alembic scenario-tests

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
	docker compose down

docker-down-destroy:
	docker compose down -v

test:
	uv run --group test pytest

test-unit:
	uv run --group test pytest tests/unit -m unit

test-cov:
	uv run --group test pytest --cov=app --cov-report=term-missing
