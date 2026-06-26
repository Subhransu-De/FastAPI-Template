from dataclasses import dataclass
import os


def _required_environment_value(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


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
            oidc_client_secret=_required_environment_value("OIDC_CLIENT_SECRET"),
            username=os.getenv("E2E_USERNAME", "e2e-user"),
            password=_required_environment_value("E2E_PASSWORD"),
            health_endpoint=os.getenv("HEALTH_ENDPOINT", "/health/db"),
        )
