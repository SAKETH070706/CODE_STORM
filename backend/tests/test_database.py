from sqlalchemy import inspect, text

from storage.database import (
    SessionLocal,
    check_database_connection,
    engine,
    init_db,
)


def test_database_connection():
    assert check_database_connection() is True


def test_database_initialization():
    init_db()

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "actions" in tables


def test_database_session():
    db = SessionLocal()

    try:
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1

    finally:
        db.close()