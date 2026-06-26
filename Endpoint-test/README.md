# Endpoint Test

Standalone Behave endpoint test application for validating the running FastAPI service.

The application expects the target service and Keycloak realm to already be running. It creates an access token in Behave's `before_all` hook and reuses that token across the endpoint scenarios.

## Environment variables

| Name | Default | Purpose |
| --- | --- | --- |
| `TARGET_BASE_URL` | `http://localhost` | Base URL for the running FastAPI application. |
| `TOKEN_URL` | `http://localhost:8080/realms/fastapi-e2e-realm/protocol/openid-connect/token` | Keycloak token endpoint. |
| `OIDC_CLIENT_ID` | `fastapi-client` | OIDC client used by the endpoint tests. |
| `OIDC_CLIENT_SECRET` | `change-me` | OIDC client secret. |
| `E2E_USERNAME` | `e2e-user` | Test user username. |
| `E2E_PASSWORD` | `test-password` | Test user password. |
| `HEALTH_ENDPOINT` | `/health/db` | Endpoint used before scenarios to wait for application readiness. |

## Run

```bash
uv sync
uv run behave
```
