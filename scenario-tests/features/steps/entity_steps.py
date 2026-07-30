from typing import Any

from behave import given, then, when

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_FORBIDDEN = 403
HTTP_CONFLICT = 409
HTTP_NOT_FOUND = 404


def require(condition: object, message: str = "Scenario assertion failed") -> None:
    if not bool(condition):
        raise AssertionError(message)


@given("the Scenario Tests application is configured")
def step_app_application_is_configured(context: Any) -> None:
    require(context.scenario_client is not None)
    require(bool(context.access_token))


@when('I create an entity named "{name}" with description "{description}"')
def step_create_entity(context: Any, name: str, description: str) -> None:
    context.expected_name = name
    context.expected_description = description
    context.create_response = context.scenario_client.create_entity(name, description)


@then("the entity creation should succeed")
def step_entity_creation_should_succeed(context: Any) -> None:
    require(
        context.create_response.status_code == HTTP_CREATED,
        context.create_response.text,
    )
    entity = context.scenario_client.response_json(context.create_response)
    require(bool(entity["id"]))
    require(entity["name"] == context.expected_name)
    require(entity["description"] == context.expected_description)
    context.entity_id = entity["id"]
    context.created_entity = entity


@when("I fetch the created entity")
def step_fetch_created_entity(context: Any) -> None:
    context.get_response = context.scenario_client.get_entity(context.entity_id)


@then("the fetched entity should match the created entity")
def step_fetched_entity_should_match(context: Any) -> None:
    require(context.get_response.status_code == HTTP_OK, context.get_response.text)
    entity = context.scenario_client.response_json(context.get_response)
    require(entity["id"] == context.entity_id)
    require(entity["name"] == context.expected_name)
    require(entity["description"] == context.expected_description)


@when("I list entities")
def step_list_entities(context: Any) -> None:
    context.list_response = context.scenario_client.list_entities()


@then("the created entity should be included in the entity list")
def step_created_entity_should_be_listed(context: Any) -> None:
    require(context.list_response.status_code == HTTP_OK, context.list_response.text)
    entities = context.scenario_client.response_json(context.list_response)
    require(any(entity["id"] == context.entity_id for entity in entities))


@when('I update the entity to name "{name}" with no description')
def step_update_entity_with_no_description(context: Any, name: str) -> None:
    context.expected_name = name
    context.expected_description = None
    context.update_response = context.scenario_client.update_entity(
        context.entity_id,
        name,
        None,
    )


@then("the entity update should succeed")
def step_entity_update_should_succeed(context: Any) -> None:
    require(context.update_response.status_code == HTTP_OK, context.update_response.text)
    entity = context.scenario_client.response_json(context.update_response)
    require(entity["id"] == context.entity_id)
    require(entity["name"] == context.expected_name)
    require(entity["description"] is None)


@when("I delete the created entity")
def step_delete_created_entity(context: Any) -> None:
    context.delete_response = context.scenario_client.delete_entity(context.entity_id)


@then("the entity deletion should succeed")
def step_entity_deletion_should_succeed(context: Any) -> None:
    require(
        context.delete_response.status_code == HTTP_NO_CONTENT,
        context.delete_response.text,
    )


@when("I fetch the deleted entity")
def step_fetch_deleted_entity(context: Any) -> None:
    context.deleted_get_response = context.scenario_client.get_entity(context.entity_id)


@then("the deleted entity should not be found")
def step_deleted_entity_should_not_be_found(context: Any) -> None:
    require(
        context.deleted_get_response.status_code == HTTP_NOT_FOUND,
        context.deleted_get_response.text,
    )


@given("the limited user has an unchanged access token")
def step_limited_user_has_token(context: Any) -> None:
    require(bool(context.limited_access_token))
    cleanup_response = context.scenario_client.remove_user_role(
        context.limited_user_id,
        "role:entity-reader",
    )
    require(
        cleanup_response.status_code == HTTP_NO_CONTENT,
        cleanup_response.text,
    )


@when("the limited user lists entities")
@when("the limited user lists entities with the same token")
def step_limited_user_lists_entities(context: Any) -> None:
    context.limited_list_response = context.scenario_client.list_entities(
        context.limited_access_token
    )


@then("the limited user should be forbidden")
def step_limited_user_should_be_forbidden(context: Any) -> None:
    require(
        context.limited_list_response.status_code == HTTP_FORBIDDEN,
        context.limited_list_response.text,
    )


@when("the administrator assigns the entity reader role")
@when("the administrator assigns the same entity reader role again")
def step_administrator_assigns_reader_role(context: Any) -> None:
    context.role_assignment_response = context.scenario_client.assign_user_role(
        context.limited_user_id,
        "role:entity-reader",
    )


@then("the role assignment should succeed")
def step_role_assignment_should_succeed(context: Any) -> None:
    require(
        context.role_assignment_response.status_code == HTTP_CREATED,
        context.role_assignment_response.text,
    )


@then("the duplicate role assignment should conflict")
def step_duplicate_role_assignment_should_conflict(context: Any) -> None:
    require(
        context.role_assignment_response.status_code == HTTP_CONFLICT,
        context.role_assignment_response.text,
    )


@then("the limited user should be allowed")
def step_limited_user_should_be_allowed(context: Any) -> None:
    require(
        context.limited_list_response.status_code == HTTP_OK,
        context.limited_list_response.text,
    )


@when("the administrator removes the entity reader role")
def step_administrator_removes_reader_role(context: Any) -> None:
    context.role_removal_response = context.scenario_client.remove_user_role(
        context.limited_user_id,
        "role:entity-reader",
    )


@then("the role removal should succeed")
def step_role_removal_should_succeed(context: Any) -> None:
    require(
        context.role_removal_response.status_code == HTTP_NO_CONTENT,
        context.role_removal_response.text,
    )
