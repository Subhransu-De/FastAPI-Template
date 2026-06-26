from dataclasses import dataclass
import os


@dataclass(frozen=True)
class EndpointTestSettings:
    target_base_url: str
    token_url: str
    oidc_client_id: str
    oidc_client_secret: str
    username: str
    password: str
    health_endpoint: str

    @classmethod
    def from_environment(cls) -> "EndpointTestSettings":
        return cls(
            target_base_url=os.getenv("TARGET_BASE_URL", "http://localhost").rstrip("/"),
            token_url=os.getenv(
                "TOKEN_URL",
                "http://localhost:8080/realms/fastapi-e2e-realm/protocol/openid-connect/token",
            ),
            oidc_client_id=os.getenv("OIDC_CLIENT_ID", "fastapi-client"),
            oidc_client_secret=os.getenv("OIDC_CLIENT_SECRET", "change-me"),
            username=os.getenv("E2E_USERNAME", "e2e-user"),
            password=os.getenv("E2E_PASSWORD", "test-password"),
            health_endpoint=os.getenv("HEALTH_ENDPOINT", "/health/db"),
        )
