FROM ghcr.io/astral-sh/uv:0.12.4 AS uv

FROM python:3.13-alpine AS builder

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --python /usr/local/bin/python --frozen --no-build --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python /usr/local/bin/python --frozen --no-build --no-dev --no-editable

FROM python:3.13-alpine

LABEL org.opencontainers.image.title="FastAPI Template"
LABEL org.opencontainers.image.description="FastAPI template"
LABEL org.opencontainers.image.vendor="Subhransu-De"
LABEL org.opencontainers.image.source="https://github.com/Subhransu-De/fastapi-template"
LABEL org.opencontainers.image.base.name="python:3.13-alpine"

WORKDIR /app

RUN python -m pip uninstall --yes pip && \
    addgroup -S app && \
    adduser -S -G app -h /app -s /sbin/nologin app

COPY --from=builder /app/.venv /app/.venv

COPY app /app/app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV APP_HOST="0.0.0.0"

EXPOSE 80

USER app

CMD ["python", "-m", "app.main"]
