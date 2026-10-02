from collections.abc import Mapping, Sequence

from sqlalchemy import Column, Connection, MetaData, Table, cast, func, select
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
        statement = insert(table).on_conflict_do_nothing().returning(*table.c)
        inserted[table.name] = len(connection.execute(statement, list(rows)).all())
        _advance_sequences(connection, table)
    return inserted


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
