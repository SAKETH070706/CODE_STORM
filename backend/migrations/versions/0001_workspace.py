"""Organization governance initial schema; leaves legacy SQLite untouched."""
revision = "0001_workspace"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
    from migrations.schema_0001 import Base
    Base.metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Destructive downgrade disabled. Restore an independently retained PostgreSQL backup instead.")
