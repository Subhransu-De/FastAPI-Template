from collections.abc import Callable

import httpx

from app.client import ScenarioTestClient
from app.config import ScenarioTestSettings

class Context:
    settings: ScenarioTestSettings
    scenario_client: ScenarioTestClient
    access_token: str
    expected_name: str
    expected_description: str | None
    entity_id: str
    create_response: httpx.Response
    get_response: httpx.Response
    list_response: httpx.Response
    update_response: httpx.Response
    delete_response: httpx.Response
    deleted_get_response: httpx.Response
    def add_cleanup(self, cleanup_func: Callable[[], object]) -> None: ...
