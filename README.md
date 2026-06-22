# FastAPI Template

![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.12.5-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.46-D71F00?style=for-the-badge&logo=sqlite&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-1.18.1-6BA81E?style=for-the-badge)

![Build Status](https://github.com/Subhransu-De/FastAPI-Template/actions/workflows/workflow.yml/badge.svg)

---

## Installation

```bash
uv sync
cp .env.example .env
```

---

## Dependency Updates

This template includes both Renovate and Dependabot configurations. They intentionally mirror each other as much as possible so forked projects can use whichever dependency update bot fits their workflow.

---

## Running the Application

### Development Mode

```bash
uv run --env-file .env python -m app.main --reload
```

### Docker-Based Development

```bash
docker compose up --build
```

---
