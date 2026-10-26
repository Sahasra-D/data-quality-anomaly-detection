
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "transactions.db"
SQL_PATH = BASE_DIR / "sql" / "phase6_queries.sql"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

sql_text = SQL_PATH.read_text(encoding="utf-8")
statements = [
    statement.strip()
    for statement in sql_text.split(";")
    if statement.strip()
]

try:
    for number, statement in enumerate(statements, start=1):
        print(f"\n{'=' * 50}")
        print(f"SQL statement {number}")
        print("=" * 50)

        cursor = conn.execute(statement)

        if cursor.description:
            rows = cursor.fetchall()
            print("Rows returned:", len(rows))

            for row in rows[:10]:
                print(dict(row))

            if len(rows) > 10:
                print("Showing first 10 rows only.")

        else:
            print("Executed successfully.")

    print("\nData-quality summary view:")
    for row in conn.execute("SELECT * FROM dq_summary"):
        print(dict(row))

    print("\nAll SQL checks completed successfully.")

except sqlite3.Error as error:
    print("\nSQL execution failed:", error)
    raise

finally:
    conn.close()
