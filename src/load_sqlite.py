
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "data" / "processed" / "transactions_anomaly_flagged.csv"
db_path = BASE_DIR / "data" / "processed" / "transactions.db"

df = pd.read_csv(csv_path)

conn = sqlite3.connect(db_path)

df.to_sql("transactions", conn, if_exists="replace", index=False)

count = conn.execute(
    "SELECT COUNT(*) FROM transactions"
).fetchone()[0]

print("SQLite database created successfully.")
print("Rows loaded:", count)
print("Columns:", len(df.columns))
print("Database:", db_path)

conn.close()
