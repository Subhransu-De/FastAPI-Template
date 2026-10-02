import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_APP_ROOT = Path("app")

_DYNAMIC_ATTRIBUTE_BUILTINS = frozenset({"getattr", "setattr", "hasattr", "delattr"})
_ESCAPE_HATCHES = frozenset({"cast", "Any"})

_ALLOWED_ESCAPE_HATCHES: frozenset[tuple[str, str]] = frozenset(
    {
        ("app/auth/openapi.py", "Any"),
    }
)


def _source_files() -> list[Path]:
    return sorted(_APP_ROOT.rglob("*.py"))


def _called_name(node: ast.Call) -> str | None:
    match node.func:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=name):
            return name
        case _:
            return None


def _referenced_names(tree: ast.AST) -> Iterator[tuple[int, str]]:
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name):
                yield node.lineno, name
            case ast.Attribute(attr=name):
                yield node.lineno, name
            case _:
                continue


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative = path.as_posix()
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _called_name(node)
            if name in _DYNAMIC_ATTRIBUTE_BUILTINS:
                violations.append(f"{relative}:{node.lineno} calls {name}()")

    for lineno, name in _referenced_names(tree):
        if name in _ESCAPE_HATCHES and (relative, name) not in _ALLOWED_ESCAPE_HATCHES:
            violations.append(f"{relative}:{lineno} uses {name}")

    return violations


@pytest.mark.parametrize("path", _source_files(), ids=lambda path: path.as_posix())
def test_application_code_stays_inside_the_type_system(path: Path) -> None:
    assert _violations(path) == []


def test_escape_hatch_allowlist_only_names_existing_files() -> None:
    existing = {path.as_posix() for path in _source_files()}

    for relative, _ in _ALLOWED_ESCAPE_HATCHES:
        assert relative in existing, relative
