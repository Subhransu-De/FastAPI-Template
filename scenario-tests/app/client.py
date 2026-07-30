import time
from typing import Any

import httpx

from app.config import ScenarioTestSettings

HTTP_OK = 200


class ScenarioTestClient:
    def __init__(self, settings: ScenarioTestSettings) -> None:
        self.settings = settings
        self.client = httpx.Client(
            base_url=settings.target_base_url,
            timeout=10.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def wait_until_ready(self, attempts: int = 30, delay_seconds: float = 2.0) -> None:
        last_error: Exception | None = None

        for _ in range(attempts):
            try:
                response = self.client.get(self.settings.health_endpoint)
                if response.status_code == HTTP_OK:
                    return
            except httpx.HTTPError as exc:
                last_error = exc

            time.sleep(delay_seconds)

        message = "FastAPI health endpoint did not become ready"
        if last_error is not None:
            message = f"{message}: {last_error}"
        raise RuntimeError(message)

    def request_access_token(
        self,
        username: str,
        password: str,
    ) -> str:
        response = httpx.post(
            self.settings.token_url,
            data={
                "grant_type": "password",
                "client_id": self.settings.oidc_client_id,
                "client_secret": self.settings.oidc_client_secret,
                "username": username,
                "password": password,
            },
            timeout=10.0,
        )
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if not access_token:
            message = "Keycloak did not return an access token"
            raise RuntimeError(message)

        return access_token

    def create_access_token(self) -> str:
        access_token = self.request_access_token(
            self.settings.username,
            self.settings.password,
        )
        self.client.headers.update({"Authorization": f"Bearer {access_token}"})
        return access_token

    def get_keycloak_user_id(self, username: str) -> str:
        keycloak_base_url, _, realm_path = self.settings.token_url.partition(
            "/realms/"
        )
        realm = realm_path.partition("/")[0]
        token_response = httpx.post(
            f"{keycloak_base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": self.settings.keycloak_admin_password,
            },
            timeout=10.0,
        )
        token_response.raise_for_status()
        response = httpx.get(
            f"{keycloak_base_url}/admin/realms/{realm}/users",
            params={"username": username, "exact": "true"},
            headers={
                "Authorization": (
                    f"Bearer {token_response.json()['access_token']}"
                )
            },
            timeout=10.0,
        )
        response.raise_for_status()
        users = response.json()
        if len(users) != 1:
            message = f"Expected exactly one Keycloak user named '{username}'"
            raise RuntimeError(message)
        return str(users[0]["id"])

    @staticmethod
    def _access_token_header(access_token: str | None) -> dict[str, str] | None:
        if access_token is None:
            return None
        return {"Authorization": f"Bearer {access_token}"}

    def create_entity(
        self,
        name: str,
        description: str | None,
        access_token: str | None = None,
    ) -> httpx.Response:
        return self.client.post(
            "/entities/",
            json={"name": name, "description": description},
            headers=self._access_token_header(access_token),
        )

    def get_entity(
        self,
        entity_id: str,
        access_token: str | None = None,
    ) -> httpx.Response:
        return self.client.get(
            f"/entities/{entity_id}",
            headers=self._access_token_header(access_token),
        )

    def list_entities(self, access_token: str | None = None) -> httpx.Response:
        return self.client.get(
            "/entities/",
            params={"limit": 100},
            headers=self._access_token_header(access_token),
        )

    def update_entity(
        self,
        entity_id: str,
        name: str,
        description: str | None,
        access_token: str | None = None,
    ) -> httpx.Response:
        return self.client.put(
            f"/entities/{entity_id}",
            json={"name": name, "description": description},
            headers=self._access_token_header(access_token),
        )

    def delete_entity(
        self,
        entity_id: str,
        access_token: str | None = None,
    ) -> httpx.Response:
        return self.client.delete(
            f"/entities/{entity_id}",
            headers=self._access_token_header(access_token),
        )

    def assign_user_role(self, user_id: str, role_name: str) -> httpx.Response:
        return self.client.post(
            f"/users/{user_id}/roles/",
            json={"role_name": role_name},
        )

    def remove_user_role(self, user_id: str, role_name: str) -> httpx.Response:
        return self.client.delete(f"/users/{user_id}/roles/{role_name}")

    @staticmethod
    def response_json(response: httpx.Response) -> Any:
        return response.json()
