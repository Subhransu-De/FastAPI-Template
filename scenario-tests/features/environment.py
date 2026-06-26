from app.client import ScenarioTestClient
from app.config import ScenarioTestSettings


def before_all(context):
    context.settings = ScenarioTestSettings()
    context.scenario_client = ScenarioTestClient(context.settings)
    context.scenario_client.wait_until_ready()
    context.access_token = context.scenario_client.create_access_token()


def after_all(context):
    scenario_client = getattr(context, "scenario_client", None)
    if scenario_client is not None:
        scenario_client.close()
