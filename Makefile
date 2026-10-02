.PHONY: help install upgrade hooks lint lint-ruff lint-format lint-ty lint-imports lint-typos format check run migrate docker-up docker-down docker-down-destroy test test-unit test-integration test-cov openapi-snapshot

help:
	@echo "Available targets:"
	@echo "  make install                   - Install all dependencies for development"
	@echo "  make upgrade                   - Upgrade all dependencies"
	@echo "  make hooks                     - Install the pre-commit hooks"
	@echo "  make check                     - Run every lint gate and the unit tests (same as CI)"
	@echo "  make lint                      - Run ruff, ruff format, ty, import-linter and typos"
	@echo "  make lint-imports              - Run import-linter architecture checks"
	@echo "  make format                    - Auto-fix ruff findings and format the code"
	@echo "  make migrate                   - Apply Alembic migrations to the configured database"
	@echo "  make run                       - Apply migrations, then start FastAPI dev server with hot reload"
	@echo "  make docker-up                 - Start full project locally"
	@echo "  make docker-down               - Stop full project locally"
	@echo "  make docker-down-destroy       - Stop full project locally and destroy volumes"
	@echo "  make test                      - Run all tests"
	@echo "  make test-unit                 - Run unit tests only"
	@echo "  make test-integration          - Run integration tests only (needs Docker)"
	@echo "  make test-cov                  - Run all tests with the coverage gate"
	@echo "  make openapi-snapshot          - Regenerate tests/contract/openapi.json"

install:
	uv sync --group lint --group migration --group test --all-packages

upgrade:
	uv sync --group lint --group migration --group test --all-packages -U

hooks:
	uvx pre-commit install --install-hooks

check: lint test-unit

lint: lint-ruff lint-format lint-ty lint-imports lint-typos

lint-ruff:
	uv run --group lint --all-packages ruff check app tests alembic scenario-tests

lint-format:
	uv run --group lint --all-packages ruff format --check app tests alembic scenario-tests

lint-ty:
	uv run --group lint --group migration --group test --all-packages ty check --error-on-warning app tests alembic scenario-tests

lint-imports:
	uv run --group lint --all-packages lint-imports --config .importlinter

lint-typos:
	uvx typos

format:
	uv run --group lint --all-packages ruff check --fix app tests alembic scenario-tests
	uv run --group lint --all-packages ruff format app tests alembic scenario-tests

run:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
	    echo "Fill in the .env file"
	fi
	uv run --group migration --env-file .env alembic -c alembic.ini upgrade head
	uv run --env-file .env python -m app.main

migrate:
	uv run --group migration --env-file .env alembic -c alembic.ini upgrade head

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-down-destroy:
	docker compose down -v

test:
	uv run --group test pytest

test-unit:
	uv run --group test pytest -m unit

test-integration:
	uv run --group test pytest -m integration

test-cov:
	uv run --group test pytest --cov --cov-report=term-missing

openapi-snapshot:
	UPDATE_OPENAPI_SNAPSHOT=1 uv run --group test pytest tests/unit/test_openapi_contract.py -q
