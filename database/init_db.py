"""Create all tables.  Run from the project root:  python -m database.init_db

(Alembic migrations replace this once the schema starts changing.)
"""
import logging

from database import models  # noqa: F401  (registers all models on Base)
from database.session import Base, engine

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("init_db")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    log.info("Created/verified %d tables: %s", len(Base.metadata.tables),
             ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    init_db()
