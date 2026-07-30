Feature: Entity endpoint scenarios
  The protected entity endpoints should support the full CRUD workflow.

  Scenario: Manage an entity through protected endpoints
    Given the Scenario Tests application is configured
    When I create an entity named "Scenario entity" with description "Created by Scenario Tests"
    Then the entity creation should succeed
    When I fetch the created entity
    Then the fetched entity should match the created entity
    When I list entities
    Then the created entity should be included in the entity list
    When I update the entity to name "Updated Scenario entity" with no description
    Then the entity update should succeed
    When I delete the created entity
    Then the entity deletion should succeed
    When I fetch the deleted entity
    Then the deleted entity should not be found

  Scenario: Apply role changes without requiring another login
    Given the limited user has an unchanged access token
    When the limited user lists entities
    Then the limited user should be forbidden
    When the administrator assigns the entity reader role
    Then the role assignment should succeed
    When the administrator assigns the same entity reader role again
    Then the duplicate role assignment should conflict
    When the limited user lists entities with the same token
    Then the limited user should be allowed
    When the administrator removes the entity reader role
    Then the role removal should succeed
    When the limited user lists entities with the same token
    Then the limited user should be forbidden
