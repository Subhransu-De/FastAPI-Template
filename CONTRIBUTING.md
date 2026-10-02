# Contributing

## Set up

```bash
make install
make hooks
cp .env.example .env
```

`make hooks` installs pre-commit hooks that run the same gates as CI. The hooks call `uv`, `actionlint` and `hadolint`, so those binaries need to be on your `PATH`.

## Before you open a pull request

1. Run `make check`. It must be green.
2. Run `make test-integration` if you touched `app/model`, `app/repository`, `app/database` or `alembic`. It needs Docker.
3. Run `make openapi-snapshot` if you changed a route, a schema or an error response, and review the resulting diff in `tests/contract/openapi.json`.
4. Read `AGENTS.md`. It lists the rules the gates enforce and the order for adding a resource.

## Pull requests

- One change per pull request. Dependency bumps and behaviour changes go separately.
- The pull request template asks which gates you ran. Answer it truthfully.
- Commit messages are one short line in the imperative, for example `Add readiness probe`.
- CI must be green before review. Do not ask for review on a red build.

## Reporting a problem

Open an issue with the behaviour you saw, the behaviour you expected, and the smallest set of steps that shows the difference. Do not include tokens, passwords or production hostnames.
