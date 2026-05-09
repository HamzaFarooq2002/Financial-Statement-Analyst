"""SQLite additive columns helper stays safe across repeated init."""

import sys
from pathlib import Path

import pytest


def _clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def test_init_db_and_column_helper_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "cols.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.resolve().as_posix()}")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "u"))
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "e"))

    _clear_app_modules()

    from app.core.database import ensure_sqlite_documents_columns, init_db

    init_db()
    assert ensure_sqlite_documents_columns() == 0
    init_db()
