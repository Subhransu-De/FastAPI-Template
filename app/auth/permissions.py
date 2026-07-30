from enum import StrEnum


class Permission(StrEnum):
    ENTITY_LIST = "entity:list"
    ENTITY_READ = "entity:read"
    ENTITY_CREATE = "entity:create"
    ENTITY_UPDATE = "entity:update"
    ENTITY_DELETE = "entity:delete"
    ROLE_LIST = "role:list"
    ROLE_ASSIGN = "role:assign"
    ROLE_REMOVE = "role:remove"
