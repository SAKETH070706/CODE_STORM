import sqlite3
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
DEMO_DB_PATH = BACKEND_DIR / "data" / "demo_sales.db"


def create_demo_database():
    DEMO_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DEMO_DB_PATH) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS sales_summary (
                month TEXT PRIMARY KEY,
                total_sales INTEGER NOT NULL
            );

            INSERT OR IGNORE INTO sales_summary
                (month, total_sales)
            VALUES
                ('January', 120000),
                ('February', 135000),
                ('March', 142000);

            CREATE TABLE IF NOT EXISTS support_summary (
                status TEXT PRIMARY KEY,
                tickets INTEGER NOT NULL
            );

            INSERT OR IGNORE INTO support_summary
                (status, tickets)
            VALUES
                ('open', 12),
                ('closed', 87);
        """)

    connection.close()
    print(f"Demo database ready: {DEMO_DB_PATH}")


if __name__ == "__main__":
    create_demo_database()
