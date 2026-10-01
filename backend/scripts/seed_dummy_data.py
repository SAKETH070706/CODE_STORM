"""Seed fresh dummy data for CODE_STORM Enterprise Workspace."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))
load_dotenv(backend_root / ".env")

from workspace.models import (
    Database,
    Organization,
    Agent,
    Task,
    Connector,
    ReviewerGroup,
    uid,
)

def seed():
    db = Database()
    print("Connecting to Neon PostgreSQL:", db.engine.url)

    with db.transaction() as s:
        org = s.query(Organization).filter(Organization.name == "CODE_STORM Workspace").first()
        if not org:
            org = s.query(Organization).first()
        if not org:
            print("Error: No organization found! Run bootstrap first.")
            return

        print(f"Target Workspace: {org.name} ({org.id})")

        # 1. Connectors (3 dummy resources)
        c_sales = Connector(
            id=uid(),
            organization_id=org.id,
            name="Sales DB",
            state="ACTIVE",
            data={"kind": "demo_sales", "destinations": []}
        )
        c_storage = Connector(
            id=uid(),
            organization_id=org.id,
            name="Report Storage",
            state="ACTIVE",
            data={"kind": "report_storage", "destinations": []}
        )
        c_outbox = Connector(
            id=uid(),
            organization_id=org.id,
            name="Outbox",
            state="ACTIVE",
            data={"kind": "simulated_delivery", "destinations": ["review@example.test"]}
        )
        s.add_all([c_sales, c_storage, c_outbox])
        s.flush()
        print(f"Created 3 Connectors: {c_sales.name}, {c_storage.name}, {c_outbox.name}")

        # 2. Agent
        agent = Agent(
            id=uid(),
            organization_id=org.id,
            name="Financial Analyst Agent",
            state="ACTIVE",
            data={"role": "data_analyst"}
        )
        s.add(agent)
        s.flush()
        print(f"Created Agent: {agent.name} (Role: {agent.data['role']})")

        # 3. Reviewer Group
        group = ReviewerGroup(
            id=uid(),
            organization_id=org.id,
            name="Security Reviewers",
            state="ACTIVE",
            data={}
        )
        s.add(group)
        s.flush()
        print(f"Created Reviewer Group: {group.name}")

        # 4. Scoped Task
        task = Task(
            id=uid(),
            organization_id=org.id,
            name="sales-report",
            state="ACTIVE",
            data={
                "description": "Sales Report Generator",
                "roles": ["data_analyst"],
                "resources": [c_sales.id, c_storage.id, c_outbox.id],
                "agents": [agent.id]
            }
        )
        s.add(task)
        s.flush()
        print(f"Created Task: {task.name} ('{task.data['description']}') with {len(task.data['resources'])} resources and 1 agent")

    print("\nDummy data seeding successfully completed! Open http://localhost:5173 to proceed with your live flow.")

if __name__ == "__main__":
    seed()
