# Working agreement

This file is for anyone changing this repository, human or agent. It states the rules the gates enforce and the order to follow when adding a feature.

## Commands

| Command                 | What it does                                                            |
| ----------------------- | ----------------------------------------------------------------------- |
| `make install`          | Installs every dependency group.                                        |
| `make hooks`            | Installs the pre-commit hooks so `make check` runs before each commit.  |
| `make check`            | Runs every lint gate and the unit tests. Green here means green in CI.  |
| `make test-integration` | Runs the Postgres tests in a disposable container. Needs Docker.        |
| `make test-cov`         | Runs all tests with the coverage floor from `pyproject.toml`.           |
| `make openapi-snapshot` | Regenerates `tests/contract/openapi.json` after an intended API change. |
| `make format`           | Applies ruff fixes and formatting.                                      |

Run `make check` before every commit. Run `make test-integration` before opening a pull request that touches the database, the models, or the migrations.

## Layers

Dependencies point downwards only. `import-linter` enforces this from `.importlinter`.

```text
app.main          builds the application from Settings; owns the lifespan
app.routes        HTTP endpoints; no persistence imports
app.service       business behaviour; talks to repositories through EntityStore
app.auth          OIDC discovery, token validation, AuthClaims, require_role
app.io            request and response schemas
app.repository    SQLAlchemy queries; Ordering and Repository[ModelType]
app.database      engine and session factory; get_sessionmaker, get_session
app.model         SQLAlchemy models
app.exceptions    BaseError, ProblemDetails, the exception handler
app.logger        stdlib logging into OpenTelemetry
app.telemetry     Logfire configuration and request attributes
app.settings      pydantic-settings models and the Settings root
```

## Rules the gates enforce

- Every function and fixture is annotated. `ruff` rule set `ANN` applies to tests as well.
- No `getattr`, `setattr`, `hasattr`, `delattr`, `cast` or `Any` in `app/`. `tests/architecture/test_type_discipline.py` fails otherwise. The only allowlisted exception is the OpenAPI document post-processing in `app/auth/openapi.py`.
- `ty` runs with `--error-on-warning`. A warning is a failure.
- Nothing happens at import time. `Settings.from_env()` is called only in `app.main.main()` and `app.main.app_from_env()`. Tests build `Settings` explicitly with `tests.support.build_settings`.
- Resources live in the lifespan. The engine, the readiness probe's single-connection engine, the session factories and the token validator are created in `app.main.lifespan` and read back through `get_sessionmaker`, `get_probe_sessionmaker` and `get_token_validator`, which are the only places that touch `request.state`. Request-scoped telemetry goes on the active span through `telemetry.record_auth_attributes`, never on `request.state`.
- Migrations that change column types say how existing values convert. Timestamp conversions use `AT TIME ZONE 'UTC'` so the session time zone cannot shift stored instants.
- Errors are RFC 9457 Problem Details. Raise a `BaseError` subclass from `app.exceptions`; never build a `JSONResponse` in a route. Declare the error statuses a route can return with `problem_responses(...)` so they appear in OpenAPI.
- The OpenAPI document is a contract. `tests/contract/openapi.json` must match the served document. Change the API, review the diff, run `make openapi-snapshot`.
- Models and migrations agree. `tests/integration/test_migrations.py` runs `alembic check` and a downgrade round trip.
- Timestamps are timezone-aware end to end: `DateTime(timezone=True)` in models, `AwareDatetime` in schemas.
- Coverage stays at or above the floor in `pyproject.toml`.
- Logfire owns the OpenTelemetry providers and the FastAPI instrumentation. FastAPI's native telemetry is constructed by `telemetry.native_telemetry_config()` with `auto_configure` off, so platform `OTEL_*` variables cannot attach a second exporter. It stays dormant while the Logfire middleware is present and takes over automatically if that middleware is removed.

## Adding a resource

Follow this order. Each step has a gate that fails until the next step is done.

1. Model in `app/model/<name>.py`, registered in `app/model/__init__.py`.
2. Migration: `uv run --group migration alembic revision --autogenerate -m "<message>"`, then read the generated file before committing it.
3. Schemas in `app/io/<name>.py`: create, update and response models. Responses use `ConfigDict(from_attributes=True)`. For a camelCase API, subclass `CamelModel` for request bodies and `CamelResponse` for responses from `app.io`. Fields stay snake_case in Python. JSON uses camelCase in both directions, and snake_case keys in a request body are rejected.
4. Repository in `app/repository/<name>.py` as a `Repository[<Model>]` subclass. Add typed query methods there, never `**kwargs`.
5. Service in `app/service/<name>.py` with a `Protocol` naming the repository methods it uses, and a `get_<name>_service` dependency in `app/service/__init__.py`.
6. Routes in `app/routes/<name>.py`. Protect writes with `Depends(require_role(...))` and declare every error status with `problem_responses(...)`. Include the router in `app/routes/__init__.py`. For a camelCase path parameter, keep the argument snake_case and write the alias inline in the signature, as `user_id: Annotated[UUID, Path(alias="userId")]` for the path `/{userId}`. Ruff's `FAST003` matches the alias only when `Path(alias=...)` appears in the signature, so do not move it into a type alias.
7. Tests: unit tests for the service with an in-memory store, integration tests for the API and repository, and `make openapi-snapshot`.
8. Keycloak: if a new role is required, add it to both realm exports in `.docker/` and to the local users.

## Do not

- Do not add module-level singletons, `global`, or settings instances outside `Settings.from_env()`.
- Do not store values on `request.state` or `app.state` outside the two accessors named above.
- Do not silence a gate with `noqa`, `type: ignore` or an allowlist entry to make a change pass. Fix the code or discuss the rule.
- Do not use `AsyncMock` or `MagicMock` for repositories or services in tests. Write a typed fake that satisfies the `Protocol`.
- Do not call `logfire.configure` in a test. Use the `capfire` fixture from `logfire.testing`; it installs and removes an in-memory exporter per test.
- Do not assert the arguments passed to a third-party library. Assert the observable result: the span that was exported, the response body that was returned, the row that was or was not written.
- Do not add a unit test for a pydantic constraint that the HTTP validation matrix in `tests/integration/test_entities_api.py` already exercises.

## Test layout

| Directory             | Runs in `make check`         | Needs      | Purpose                                                             |
| --------------------- | ---------------------------- | ---------- | ------------------------------------------------------------------- |
| `tests/architecture`  | yes                          | nothing    | Type discipline over `app/`.                                        |
| `tests/unit`          | yes                          | SQLite     | Behaviour of one module; typed fakes, `capfire`, no network.        |
| `tests/unit/property` | yes                          | Hypothesis | Parsing boundaries: `AuthClaims` and the request schemas.           |
| `tests/integration`   | no (`make test-integration`) | Docker     | Real Postgres, real RS256 tokens, migrations, spans, JWKS rotation. |
| `tests/contract`      | yes                          | nothing    | The committed OpenAPI document.                                     |
| `scenario-tests`      | CI e2e job                   | Compose    | Behave walk against the running stack with a Keycloak token.        |

Test order is randomized by `pytest-randomly` and every test has a 30 second timeout. Warnings are errors. Mutation testing runs weekly from `.github/workflows/quality-weekly.yml` and publishes surviving mutants as an artifact.
