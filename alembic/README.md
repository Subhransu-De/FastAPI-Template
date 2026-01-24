# Common Commands

| Command                               | Description                                         |
| ------------------------------------- | --------------------------------------------------- |
| `uv run alembic current`              | Show current revision                               |
| `uv run alembic history`              | Show migration history                              |
| `uv run alembic upgrade head`         | Apply all pending migrations                        |
| `uv run alembic upgrade +1`           | Apply next migration                                |
| `uv run alembic downgrade -1`         | Rollback one migration                              |
| `uv run alembic downgrade base`       | Rollback all migrations                             |
| `uv run alembic downgrade <revision>` | Rollback to specific revision                       |
| `uv run alembic stamp head`           | Mark database as current without running migrations |
