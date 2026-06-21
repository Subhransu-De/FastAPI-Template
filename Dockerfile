FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.title="FastAPI Template"
LABEL org.opencontainers.image.description="FastAPI template"
LABEL org.opencontainers.image.vendor="Subhransu-De"
LABEL org.opencontainers.image.source="https://github.com/Subhransu-De/fastapi-template"
LABEL org.opencontainers.image.base.name="python:3.13-slim-bookworm"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY alembic.ini /app/
COPY alembic /app/alembic
COPY app /app/app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV APP_HOST="0.0.0.0"

EXPOSE 80

CMD ["python", "-m", "app.main"]
