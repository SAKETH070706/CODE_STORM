"""Reset all workspace tenant data while preserving Users, Passwords, and Memberships."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is on path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))
load_dotenv(backend_root / ".env")

from workspace.models import (
    Database,
    Base,
    User,
    Membership,
    Organization,
    Source,
    Policy,
    Agent,
    Task,
    Connector,
    ReviewerGroup,
    Action,
    Artifact,
    Approval,
    Outbox,
    CompilationJob,
    Credential,
    Idempotency,
    AuditEvent,
    LegacyStream,
)

def reset_data():
    db = Database()
    print("Connected to database:", db.engine.url)

    with db.transaction() as s:
        # Delete dependent tables first
        deleted_counts = {}
        for model in [
            Idempotency,
            AuditEvent,
            Outbox,
            Approval,
            Artifact,
            Action,
            Credential,
            CompilationJob,
            Task,
            Connector,
            Agent,
            ReviewerGroup,
            Policy,
            Source,
            LegacyStream,
        ]:
            count = s.query(model).delete()
            deleted_counts[model.__tablename__] = count
            print(f"Cleared {count} rows from {model.__tablename__}")

        # Reset organization state
        orgs = s.query(Organization).all()
        for org in orgs:
            org.active_policy_id = None
            org.audit_sequence = 0
            org.audit_head = "0" * 64
        print(f"Reset {len(orgs)} organizations to clean state")

        # Verify users and memberships are intact
        users = s.query(User).all()
        memberships = s.query(Membership).all()
        print(f"Preserved {len(users)} users: {[u.email for u in users]}")
        print(f"Preserved {len(memberships)} memberships")

    # Also clean SQLite governor.db if it exists
    gov_db_path = backend_root / "data" / "governor.db"
    if gov_db_path.exists():
        import sqlite3
        with sqlite3.connect(gov_db_path) as conn:
            cur = conn.cursor()
            for tbl in ["actions", "governed_actions", "task_assignments", "idempotency", "approvals", "artifacts", "outbox", "audit_events"]:
                try:
                    cur.execute(f"DELETE FROM {tbl}")
                    print(f"Cleared SQLite table {tbl}")
                except Exception as e:
                    pass
            conn.commit()

    print("\nDatabase reset successfully complete! Only user accounts and passwords remain.")

if __name__ == "__main__":
    reset_data()
