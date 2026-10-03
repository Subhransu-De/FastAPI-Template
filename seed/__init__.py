from collections.abc import Mapping, Sequence
from itertools import groupby

from sqlalchemy import (
    Connection,
    MetaData,
    Table,
    cast,
    column,
    func,
    select,
    table,
    text,
)
from sqlalchemy.dialects.postgresql import REGCLASS, insert

type Row = Mapping[str, object]
type Fixtures = Mapping[str, Sequence[Row]]

_PG_CLASS = table("pg_class", column("oid"), column("relname"), column("relnamespace"))
_PG_NAMESPACE = table("pg_namespace", column("oid"), column("nspname"))


def seed(connection: Connection, fixtures: Fixtures) -> dict[str, int]:
    metadata = MetaData()
    metadata.reflect(bind=connection, only=list(fixtures))
    inserted: dict[str, int] = {}
    for seeded_table in metadata.sorted_tables:
        rows = fixtures.get(seeded_table.name)
        if seeded_table.schema is not None or not rows:
            continue
        _require_primary_keys(seeded_table, rows)
        _lock_against_writers(connection, seeded_table)
        inserted[seeded_table.name] = _insert_rows(connection, seeded_table, rows)
        _restart_identity_sequences(connection, seeded_table)
    return inserted


def _require_primary_keys(seeded_table: Table, rows: Sequence[Row]) -> None:
    key = [column.name for column in seeded_table.primary_key.columns]
    if not key or any(row.get(name) is None for row in rows for name in key):
        msg = f"{seeded_table.name} fixture rows must set the primary key {key}"
        raise ValueError(msg)


def _lock_against_writers(connection: Connection, seeded_table: Table) -> None:
    table_name = connection.dialect.identifier_preparer.format_table(seeded_table)
    connection.execute(text(f"LOCK TABLE {table_name} IN SHARE ROW EXCLUSIVE MODE"))


def _insert_rows(
    connection: Connection, seeded_table: Table, rows: Sequence[Row]
) -> int:
    key = list(seeded_table.primary_key.columns)
    statement = (
        insert(seeded_table).on_conflict_do_nothing(index_elements=key).returning(*key)
    )
    return sum(
        len(connection.execute(statement, list(batch)).all())
        for _, batch in groupby(rows, key=frozenset)
    )


def _restart_identity_sequences(connection: Connection, seeded_table: Table) -> None:
    table_name = connection.dialect.identifier_preparer.format_table(seeded_table)
    for key_column in seeded_table.primary_key.columns:
        sequence = connection.scalar(
            select(func.pg_get_serial_sequence(table_name, key_column.name))
        )
        if sequence is None:
            continue
        highest = connection.execute(select(func.max(key_column))).scalar_one()
        if highest >= _next_value(connection, sequence):
            connection.execute(
                text(f"ALTER SEQUENCE {sequence} RESTART WITH {int(highest) + 1}")
            )


def _next_value(connection: Connection, sequence: str) -> int:
    schema, name = connection.execute(
        select(_PG_NAMESPACE.c.nspname, _PG_CLASS.c.relname)
        .join_from(
            _PG_CLASS, _PG_NAMESPACE, _PG_CLASS.c.relnamespace == _PG_NAMESPACE.c.oid
        )
        .where(_PG_CLASS.c.oid == cast(sequence, REGCLASS))
    ).one()
    state = table(name, column("last_value"), column("is_called"), schema=schema)
    last_value, is_called = connection.execute(
        select(state.c.last_value, state.c.is_called)
    ).one()
    return last_value + 1 if is_called else last_value
