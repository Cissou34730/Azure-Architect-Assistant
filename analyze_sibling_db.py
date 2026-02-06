import sqlite3
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
print(f"Analyzing: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

for table in tables:
    cursor.execute(f"SELECT count(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Table {table}: {count} rows")

conn.close()
