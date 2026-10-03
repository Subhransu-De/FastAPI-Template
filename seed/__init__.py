from collections.abc import Mapping, Sequence
from itertools import groupby

from sqlalchemy import Connection, MetaData, Table, func, select, text
from sqlalchemy.dialects.postgresql import insert

type Row = Mapping[str, object]
type Fixtures = Mapping[str, Sequence[Row]]


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
    for column in seeded_table.primary_key.columns:
        sequence = connection.scalar(
            select(func.pg_get_serial_sequence(table_name, column.name))
        )
        if sequence is None:
            continue
        highest = connection.execute(select(func.max(column))).scalar_one()
        connection.execute(
            text(f"ALTER SEQUENCE {sequence} RESTART WITH {int(highest) + 1}")
        )
