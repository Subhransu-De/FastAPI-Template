from base64 import urlsafe_b64decode
from http import HTTPStatus

from behave import given, then, when
from behave.runner import Context
from pydantic import BaseModel


class RealmAccess(BaseModel):
    roles: list[str]


class AccessTokenClaims(BaseModel):
    realm_access: RealmAccess
    resource_access: dict[str, object] | None = None


def require(condition: object, message: str = "Scenario assertion failed") -> None:
    if not bool(condition):
        raise AssertionError(message)


@given("the Scenario Tests application is configured")
def step_app_application_is_configured(context: Context) -> None:
    require(context.scenario_client is not None)
    require(bool(context.access_token))


@then("the access token should grant only the entity write role")
def step_access_token_grants_only_entity_write(context: Context) -> None:
    payload = context.access_token.split(".")[1]
    claims = AccessTokenClaims.model_validate_json(
        urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    require(claims.realm_access.roles == ["entities:write"])
    require(not claims.resource_access)


@when('I create an entity named "{name}" with description "{description}"')
def step_create_entity(context: Context, name: str, description: str) -> None:
    context.expected_name = name
    context.expected_description = description
    context.create_response = context.scenario_client.create_entity(name, description)


@then("the entity creation should succeed")
def step_entity_creation_should_succeed(context: Context) -> None:
    require(
        context.create_response.status_code == HTTPStatus.CREATED,
        context.create_response.text,
    )
    entity = context.scenario_client.entity_from(context.create_response)
    require(bool(entity.id))
    require(entity.name == context.expected_name)
    require(entity.description == context.expected_description)
    context.entity_id = entity.id


@when("I fetch the created entity")
def step_fetch_created_entity(context: Context) -> None:
    context.get_response = context.scenario_client.get_entity(context.entity_id)


@then("the fetched entity should match the created entity")
def step_fetched_entity_should_match(context: Context) -> None:
    require(
        context.get_response.status_code == HTTPStatus.OK, context.get_response.text
    )
    entity = context.scenario_client.entity_from(context.get_response)
    require(entity.id == context.entity_id)
    require(entity.name == context.expected_name)
    require(entity.description == context.expected_description)


@when("I list entities")
def step_list_entities(context: Context) -> None:
    context.list_response = context.scenario_client.list_entities()


@then("the created entity should be included in the entity list")
def step_created_entity_should_be_listed(context: Context) -> None:
    require(
        context.list_response.status_code == HTTPStatus.OK, context.list_response.text
    )
    entities = context.scenario_client.entities_from(context.list_response)
    require(any(entity.id == context.entity_id for entity in entities))


@when('I update the entity to name "{name}" with no description')
def step_update_entity_with_no_description(context: Context, name: str) -> None:
    context.expected_name = name
    context.expected_description = None
    context.update_response = context.scenario_client.update_entity(
        context.entity_id,
        name,
        None,
    )


@then("the entity update should succeed")
def step_entity_update_should_succeed(context: Context) -> None:
    require(
        context.update_response.status_code == HTTPStatus.OK,
        context.update_response.text,
    )
    entity = context.scenario_client.entity_from(context.update_response)
    require(entity.id == context.entity_id)
    require(entity.name == context.expected_name)
    require(entity.description is None)


@when("I delete the created entity")
def step_delete_created_entity(context: Context) -> None:
    context.delete_response = context.scenario_client.delete_entity(context.entity_id)


@then("the entity deletion should succeed")
def step_entity_deletion_should_succeed(context: Context) -> None:
    require(
        context.delete_response.status_code == HTTPStatus.NO_CONTENT,
        context.delete_response.text,
    )


@when("I fetch the deleted entity")
def step_fetch_deleted_entity(context: Context) -> None:
    context.deleted_get_response = context.scenario_client.get_entity(context.entity_id)


@then("the deleted entity should not be found")
def step_deleted_entity_should_not_be_found(context: Context) -> None:
    require(
        context.deleted_get_response.status_code == HTTPStatus.NOT_FOUND,
        context.deleted_get_response.text,
    )
