from typing import Any

from app.client import ScenarioTestClient
from app.config import ScenarioTestSettings


def before_all(context: Any) -> None:
    context.settings = ScenarioTestSettings()
    context.scenario_client = ScenarioTestClient(context.settings)
    context.scenario_client.wait_until_ready()
    context.access_token = context.scenario_client.create_access_token()
    context.limited_access_token = context.scenario_client.request_access_token(
        context.settings.limited_username,
        context.settings.limited_password,
    )
    context.limited_user_id = context.scenario_client.get_keycloak_user_id(
        context.settings.limited_username
    )


def after_all(context: Any) -> None:
    scenario_client = getattr(context, "scenario_client", None)
    if scenario_client is not None:
        scenario_client.close()
