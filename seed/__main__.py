import logging

from sqlalchemy import create_engine, pool

from app.settings import DatabaseSettings
from seed import seed
from seed.fixtures import FIXTURES

logger = logging.getLogger("seed")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    database = DatabaseSettings()
    engine = create_engine(database.url, poolclass=pool.NullPool)
    try:
        with engine.begin() as connection:
            inserted = seed(connection, FIXTURES)
    finally:
        engine.dispose()
    for table, count in inserted.items():
        logger.info("%s: %d new rows", table, count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
