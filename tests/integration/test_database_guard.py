import pytest
from sqlalchemy.engine import make_url

from tests.integration.conftest import DOCKER_COMPOSE_DATABASE_URL

pytestmark = pytest.mark.integration


def test_testcontainers_database_url_is_not_docker_compose_db(
    test_postgres_url: str,
) -> None:
    parsed = make_url(test_postgres_url)

    assert "@db:5432/fastapi_db" not in test_postgres_url
    assert parsed.host != "db"
    assert test_postgres_url != DOCKER_COMPOSE_DATABASE_URL
