# Scenario Tests

Standalone Behave Scenario Tests application for validating the running FastAPI service.

The application expects the target service and Keycloak realm to already be running. It verifies CRUD access and proves that role assignment and removal change a second user's access while that user keeps the same access token.

## Environment variables

| Name | Default | Purpose |
| --- | --- | --- |
| `TARGET_BASE_URL` | `http://localhost` | Base URL for the running FastAPI application. |
| `TOKEN_URL` | `http://localhost:8080/realms/fastapi-e2e-realm/protocol/openid-connect/token` | Keycloak token endpoint. |
| `OIDC_CLIENT_ID` | `fastapi-client` | OIDC client used by the Scenario Testss. |
| `OIDC_CLIENT_SECRET` | Required | OIDC client secret. |
| `E2E_USERNAME` | `e2e-user` | Test user username. |
| `E2E_PASSWORD` | Required | Test user password. |
| `E2E_LIMITED_USERNAME` | `limited-user` | User used to test live role changes. |
| `E2E_LIMITED_PASSWORD` | `test-password` | Limited user's password. |
| `KEYCLOAK_ADMIN_PASSWORD` | Required | Used only to resolve the limited user's Keycloak ID. |
| `HEALTH_ENDPOINT` | `/health` | Endpoint used before scenarios to wait for application readiness. |

## Run

```bash
uv sync
uv run behave
```
