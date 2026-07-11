# Local Keycloak

The Compose stack runs Keycloak 26.7 in development mode. It is local test infrastructure, not a production Keycloak configuration.

## Realm

`docker-compose.yml` starts Keycloak with `start-dev --import-realm` and imports `.docker/realm-export.json` as `fastapi-realm`.

Keycloak has no persistent data volume. Recreating the container resets it to the committed realm export. This keeps fresh local stacks reproducible.

## Clients

| Client           | Purpose            | Configuration                                                 |
| ---------------- | ------------------ | ------------------------------------------------------------- |
| `fastapi-docs`   | Swagger UI login   | Public authorization-code client with PKCE; no browser secret |
| `fastapi-client` | API token audience | Confidential local client; the API validates its audience     |

The `keycloak-config` one-shot service replaces the Swagger redirect URI and web origin with the current `APP_PUBLIC_URL`. Exact URLs are used because wildcard browser callbacks are unsafe and break isolated stacks on alternate ports.

The browser uses the host-facing issuer, such as `http://localhost:8080`. The API fetches Keycloak metadata and keys through the internal Compose address, `http://keycloak:8080`. Tokens still retain the public issuer.

## Local identities

- Keycloak administrator: `admin`; its password comes from `KEYCLOAK_ADMIN_PASSWORD`.
- Local user: `testuser` / `testuser@example.com`.

`testuser` has no initial password. The local browser flow accepts the known username, skips the absent password check, and immediately requires the user to create a password. Recreating Keycloak removes that password.

This password-claiming behavior is intentional local convenience. It must not be copied into a production realm.

## Scenario-test realm

`docker-compose.e2e.yml` replaces the normal import with `.docker/e2e-realm-export.json`. That realm is `fastapi-e2e-realm` and contains the fixed `e2e-user` identity used by automated scenario tests. Its credentials are test fixtures only.
