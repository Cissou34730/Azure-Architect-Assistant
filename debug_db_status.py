import sqlite3
import os
import sys

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
print(f"Checking DB at: {os.path.abspath(db_path)}")
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Projects ---")
    projects = cursor.execute("SELECT id, name FROM projects").fetchall()
    print(f"Found {len(projects)} projects")
    for p in projects:
        print(p)
    
    print("\n--- Checklists ---")
    checklists = cursor.execute("SELECT id, project_id, title FROM checklists").fetchall()
    print(f"Found {len(checklists)} checklists")
    for c in checklists:
        print(c)
    
    print("\n--- Project States ---")
    states = cursor.execute("SELECT project_id, length(state) FROM project_states").fetchall()
    print(f"Found {len(states)} project states")
    for s in states:
        print(s)

    print("\n--- All Tables ---")
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print([t[0] for t in tables])
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
