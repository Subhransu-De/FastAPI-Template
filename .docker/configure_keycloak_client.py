# ruff: noqa: INP001
"""Configure the Keycloak client for the current Compose project."""

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_KEYCLOAK_URL = "http://localhost:8080"
_AUTH_ATTEMPTS = 10
_AUTH_RETRY_SECONDS = 2.0


def _get_admin_token(client: httpx.Client, password: str) -> str:
    last_error: Exception | None = None
    for _ in range(_AUTH_ATTEMPTS):
        try:
            response = client.post(
                "/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": "admin",
                    "password": password,
                },
            )
            response.raise_for_status()
            return str(response.json()["access_token"])
        except (httpx.HTTPError, KeyError) as exc:
            last_error = exc
            time.sleep(_AUTH_RETRY_SECONDS)

    message = f"Could not authenticate to Keycloak after {_AUTH_ATTEMPTS} attempts"
    raise RuntimeError(message) from last_error


def _get_keycloak_client_representation(
    client: httpx.Client,
    realm: str,
    client_id: str,
) -> dict[str, Any]:
    response = client.get(
        f"/admin/realms/{realm}/clients",
        params={"clientId": client_id},
    )
    response.raise_for_status()
    matches = response.json()
    if len(matches) != 1:
        message = f"Expected one '{client_id}' client in realm '{realm}'"
        raise RuntimeError(message)
    return dict(matches[0])


def configure_keycloak_client() -> None:
    realm = os.environ["OIDC_REALM"]
    client_id = os.environ["OIDC_DOCS_CLIENT_ID"]
    app_public_url = os.environ["APP_PUBLIC_URL"].rstrip("/")

    with httpx.Client(base_url=_KEYCLOAK_URL, timeout=10.0) as client:
        token = _get_admin_token(client, os.environ["KEYCLOAK_ADMIN_PASSWORD"])
        client.headers["Authorization"] = f"Bearer {token}"
        representation = _get_keycloak_client_representation(
            client,
            realm,
            client_id,
        )
        representation["redirectUris"] = [
            f"{app_public_url}/docs/oauth2-redirect"
        ]
        representation["webOrigins"] = [app_public_url]
        response = client.put(
            f"/admin/realms/{realm}/clients/{representation['id']}",
            json=representation,
        )
        response.raise_for_status()

    logger.info(
        "Configured %s redirect URI: %s/docs/oauth2-redirect",
        client_id,
        app_public_url,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    configure_keycloak_client()
