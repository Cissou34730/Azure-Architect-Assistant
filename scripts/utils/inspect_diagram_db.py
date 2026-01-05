import os
import sqlite3

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

PATHS = [
    os.path.join(REPO, 'backend', 'data', 'diagram.db'),
    os.path.join(REPO, 'data', 'diagrams.db'),
]

def inspect_db(path: str) -> None:
    print(f"DB path: {path} exists: {os.path.exists(path)}")
    if not os.path.exists(path):
        return
    print(f"\n=== Inspecting {path}")
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]  
    print("Tables:", tables)
    for t in tables:
        schema = cur.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()
        print(f"\nTable: {t}")
        print("Schema:", schema[0] if schema else "N/A")
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print("Row count:", count)
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
        rows = cur.execute(f"SELECT * FROM {t} LIMIT 3").fetchall()
        print("Sample rows (up to 3):")
        for r in rows:
            print(dict(zip(cols, r)))
    conn.close()
    print(f"\n--- End inspection for {path}\n")

if __name__ == '__main__':
    for p in PATHS:
        inspect_db(p)
