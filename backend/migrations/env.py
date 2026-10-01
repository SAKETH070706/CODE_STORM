from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as backend_config  # load backend/.env for operator migration commands
from workspace.models import Base
config = context.config
def _normalize_migration_url(raw_url: str) -> str:
    if not raw_url:
        return "sqlite:///code_storm.db"
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

raw_db_url = os.getenv("DATABASE_URL") or getattr(backend_config, "DATABASE_URL", "sqlite:///code_storm.db")
db_url = _normalize_migration_url(raw_db_url)
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
if context.is_offline_mode():
    context.configure(url=db_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
