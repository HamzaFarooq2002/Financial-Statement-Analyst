from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_documents_columns() -> int:
    """Add missing columns on `documents` for SQLite-only drift vs. ORM model.

    Returns number of ALTER TABLE statements executed.
    """
    if not settings.database_url.startswith("sqlite"):
        return 0

    alterations: list[tuple[str, str]] = [
        ("report_year", "INTEGER"),
        ("company_name", "VARCHAR(255)"),
        ("parent_document_id", "INTEGER REFERENCES documents(id)"),
    ]

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
        existing = {row[1] for row in rows}

        executed = 0
        for column_name, column_def in alterations:
            if column_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {column_def}"))
            executed += 1

        conn.commit()
        return executed


def init_db() -> None:
    from app.models.document import Document  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_documents_columns()

