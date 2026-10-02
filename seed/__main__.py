import logging
import os

from sqlalchemy import create_engine, pool

from seed import seed
from seed.fixtures import FIXTURES

logger = logging.getLogger("seed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        msg = "DATABASE_URL must be set to seed the database"
        raise RuntimeError(msg)
    engine = create_engine(database_url, poolclass=pool.NullPool)
    try:
        with engine.begin() as connection:
            inserted = seed(connection, FIXTURES)
    finally:
        engine.dispose()
    for table, count in inserted.items():
        logger.info("%s: %d new rows", table, count)


if __name__ == "__main__":
    main()
