from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------

load_dotenv(BACKEND_DIR / ".env")


# ---------------------------------------------------------
# DATABASE URL
# ---------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/governor.db",
)


# ---------------------------------------------------------
# SQLALCHEMY ENGINE
# ---------------------------------------------------------

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


# ---------------------------------------------------------
# SESSION
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------
# BASE MODEL
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# DATABASE SESSION DEPENDENCY
# ---------------------------------------------------------

def get_db():
    """
    Provides a database session for FastAPI endpoints
    or other backend services.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# INITIALIZE DATABASE
# ---------------------------------------------------------

def init_db():
    """
    Creates all registered SQLAlchemy tables.

    Importing models before create_all() ensures that
    SQLAlchemy knows about the models.
    """

    from storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# DATABASE CONNECTION CHECK
# ---------------------------------------------------------

def check_database_connection() -> bool:
    """
    Returns True when the database connection is working.
    """

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False