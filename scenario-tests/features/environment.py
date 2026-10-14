from behave.runner import Context

from app.client import ScenarioTestClient
from app.config import ScenarioTestSettings


def before_all(context: Context) -> None:
    context.settings = ScenarioTestSettings()
    scenario_client = ScenarioTestClient(context.settings)
    context.add_cleanup(scenario_client.close)
    context.scenario_client = scenario_client
    scenario_client.wait_until_ready()
    context.access_token = scenario_client.create_access_token()
