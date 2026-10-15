from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base, EvalRun

_settings = get_settings()
connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
engine = create_engine(_settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _sqlite_fk(dbapi_conn, _):
    if _settings.database_url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


_ADDED_COLUMNS = {
    "eval_runs": {
        "dataset_version": "VARCHAR(64) DEFAULT ''",
        "pass_rate": "FLOAT",
        "n_cases": "INTEGER",
        "n_failed": "INTEGER",
        "critical_failed": "INTEGER DEFAULT 0",
        "regression_delta": "FLOAT",
        "regression_alert": "BOOLEAN DEFAULT 0",
        "p95_latency_ms": "FLOAT",
        "score_stderr": "FLOAT",
    },
    "eval_results": {
        "assertion": "VARCHAR(32) DEFAULT ''",
        "passed": "BOOLEAN DEFAULT 0",
        "latency_ms": "FLOAT",
        "error": "TEXT DEFAULT ''",
        "rubric_json": "TEXT DEFAULT ''",
    },
}


def _migrate_sqlite() -> None:
    if not _settings.database_url.startswith("sqlite"):
        return
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if not insp.has_table(table):
                continue
            existing = {col["name"] for col in insp.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_is_empty(db: Session) -> bool:
    return db.scalar(select(EvalRun.id).limit(1)) is None
