# Environment Variables

`.env.example` is the reference for the root `.env` file. Replace any applicable `<placeholder>` value before use.

**Required by** describes when a value must be supplied. Compose injects several application values itself, so host-run and Compose requirements differ.

## Application

| Key        | Required by | Meaning                                                        |
| ---------- | ----------- | -------------------------------------------------------------- |
| `APP_NAME` | Optional    | Name shown in FastAPI metadata.                                |
| `APP_HOST` | Optional    | Host interface for a host-run API. Default: `127.0.0.1`.       |
| `PORT`     | Optional    | API listening port. Default: `80`.                             |
| `RELOAD`   | Optional    | Enables Uvicorn reload for host development. Default: `False`. |

## Compose

| Key                       | Required by | Meaning                                                                                |
| ------------------------- | ----------- | -------------------------------------------------------------------------------------- |
| `COMPOSE_PROJECT_NAME`    | Optional    | Isolates Compose containers, networks, volumes, and default image names.               |
| `APP_PORT`                | Optional    | Host port mapped to the API. Default: `80`.                                            |
| `APP_PUBLIC_URL`          | Optional    | Browser-visible API origin used for the Swagger callback. Default: `http://localhost`. |
| `KEYCLOAK_PORT`           | Optional    | Host port mapped to Keycloak. Default: `8080`.                                         |
| `OIDC_PUBLIC_URL`         | Optional    | Browser-visible Keycloak origin and token issuer. Default: `http://localhost:8080`.    |
| `APP_IMAGE`               | Optional    | Local API image name.                                                                  |
| `MIGRATION_IMAGE`         | Optional    | Local migration image name.                                                            |
| `POSTGRES_PASSWORD`       | **Compose** | Password for the local PostgreSQL service.                                             |
| `KEYCLOAK_ADMIN_PASSWORD` | **Compose** | Password for the local `admin` account and configuration service.                      |

A minimal Compose `.env` needs only:

```dotenv
POSTGRES_PASSWORD=local-postgres
KEYCLOAK_ADMIN_PASSWORD=local-keycloak
```

## Database

| Key                      | Required by  | Meaning                                                                 |
| ------------------------ | ------------ | ----------------------------------------------------------------------- |
| `DATABASE_URL`           | **Host run** | PostgreSQL connection URL. Compose creates its own internal URL.        |
| `DATABASE_POOL_SIZE`     | Optional     | Number of persistent connections in the host-run pool. Default: `5`.    |
| `DATABASE_MAX_OVERFLOW`  | Optional     | Extra temporary connections allowed above the pool size. Default: `10`. |
| `DATABASE_ECHO`          | Optional     | Logs generated SQL when enabled. Default: `False`.                      |
| `DATABASE_POOL_PRE_PING` | Optional     | Checks pooled connections before reuse. Default: `True`.                |

## OIDC

| Key                           | Required by         | Meaning                                                                                           |
| ----------------------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| `OIDC_ISSUER_URL`             | **Host run**        | Public realm URL used for discovery and issuer validation.                                        |
| `OIDC_INTERNAL_URL`           | Optional            | Internal URL used to fetch discovery metadata and signing keys while retaining the public issuer. |
| `OIDC_CLIENT_ID`              | **Host run**        | Audience expected in API access tokens.                                                           |
| `OIDC_DOCS_CLIENT_ID`         | **Host run**        | Public PKCE client used by Swagger UI.                                                            |
| `OIDC_CLIENT_SECRET`          | Scenario tests only | Confidential client credential; the main API and Swagger UI do not use it.                        |
| `OIDC_JWKS_CACHE_TTL_SECONDS` | Optional            | Signing-key cache duration in seconds. Default: `300`.                                            |

Compose supplies the issuer and client IDs for its local realm.

## OIDC discovery overrides

These keys are optional as a group. If one is set, all four must be set; partial overrides are rejected at startup.

| Key                           | Meaning                                            |
| ----------------------------- | -------------------------------------------------- |
| `OIDC_JWKS_URI`               | Signing-key endpoint used by the API.              |
| `OIDC_ISSUER`                 | Exact issuer expected in tokens.                   |
| `OIDC_AUTHORIZATION_ENDPOINT` | Browser authorization endpoint used by Swagger UI. |
| `OIDC_TOKEN_ENDPOINT`         | Token endpoint used by Swagger UI.                 |

The overrides bypass network discovery. They are mainly useful for tests, fixed infrastructure, or air-gapped environments.
