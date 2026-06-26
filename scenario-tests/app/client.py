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

    def create_access_token(self) -> str:
        response = httpx.post(
            self.settings.token_url,
            data={
                "grant_type": "password",
                "client_id": self.settings.oidc_client_id,
                "client_secret": self.settings.oidc_client_secret,
                "username": self.settings.username,
                "password": self.settings.password,
            },
            timeout=10.0,
        )
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if not access_token:
            message = "Keycloak did not return an access token"
            raise RuntimeError(message)

        self.client.headers.update({"Authorization": f"Bearer {access_token}"})
        return access_token

    def create_entity(self, name: str, description: str | None) -> httpx.Response:
        return self.client.post(
            "/entities/",
            json={"name": name, "description": description},
        )

    def get_entity(self, entity_id: str) -> httpx.Response:
        return self.client.get(f"/entities/{entity_id}")

    def list_entities(self) -> httpx.Response:
        return self.client.get("/entities/")

    def update_entity(
        self,
        entity_id: str,
        name: str,
        description: str | None,
    ) -> httpx.Response:
        return self.client.put(
            f"/entities/{entity_id}",
            json={"name": name, "description": description},
        )

    def delete_entity(self, entity_id: str) -> httpx.Response:
        return self.client.delete(f"/entities/{entity_id}")

    @staticmethod
    def response_json(response: httpx.Response) -> Any:
        return response.json()
