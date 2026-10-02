from collections.abc import Mapping, Sequence
from typing import Literal

from sqlalchemy import Column, Connection, MetaData, Table, cast, func, select, text
from sqlalchemy.dialects.postgresql import REGCLASS, insert

type Row = Mapping[str, object]
type Fixtures = Mapping[str, Sequence[Row]]


def seed(connection: Connection, fixtures: Fixtures) -> dict[str, int]:
    metadata = MetaData()
    metadata.reflect(bind=connection, only=list(fixtures))
    inserted: dict[str, int] = {}
    for table in metadata.sorted_tables:
        rows = fixtures.get(table.name)
        if not rows:
            continue
        _lock_against_writers(connection, table)
        always_identities = [
            column.name
            for column in table.c
            if column.identity is not None
            and column.identity.always
            and any(column.name in row for row in rows)
        ]
        _set_identity_generation(connection, table, always_identities, "BY DEFAULT")
        statement = insert(table).on_conflict_do_nothing().returning(*table.c)
        inserted[table.name] = len(connection.execute(statement, list(rows)).all())
        _set_identity_generation(connection, table, always_identities, "ALWAYS")
        _advance_sequences(connection, table)
    return inserted


def _lock_against_writers(connection: Connection, table: Table) -> None:
    table_name = connection.dialect.identifier_preparer.format_table(table)
    connection.execute(text(f"LOCK TABLE {table_name} IN SHARE ROW EXCLUSIVE MODE"))


def _set_identity_generation(
    connection: Connection,
    table: Table,
    columns: Sequence[str],
    generation: Literal["ALWAYS", "BY DEFAULT"],
) -> None:
    preparer = connection.dialect.identifier_preparer
    for column in columns:
        connection.execute(
            text(
                f"ALTER TABLE {preparer.format_table(table)} "
                f"ALTER COLUMN {preparer.quote(column)} SET GENERATED {generation}"
            )
        )


def _advance_sequences(connection: Connection, table: Table) -> None:
    table_name = connection.dialect.identifier_preparer.format_table(table)
    for column in table.c:
        sequence = connection.scalar(
            select(func.pg_get_serial_sequence(table_name, column.name))
        )
        if sequence is not None:
            _advance_sequence(connection, table, column, sequence)


def _advance_sequence(
    connection: Connection,
    table: Table,
    column: Column[object],
    sequence: str,
) -> None:
    sequence_id = cast(sequence, REGCLASS)
    highest = select(func.max(column)).select_from(table).scalar_subquery()
    last_value = func.coalesce(func.pg_sequence_last_value(sequence_id), highest)
    connection.execute(
        select(func.setval(sequence_id, func.greatest(highest, last_value)))
    )
