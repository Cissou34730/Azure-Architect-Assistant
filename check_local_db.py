import sqlite3
import os

db_path = 'backend/data/projects.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Projects ---")
    projects = cursor.execute("SELECT id, name FROM projects").fetchall()
    for p in projects:
        print(p)
    
    # Check for checklists
    print("\n--- Checklists ---")
    try:
        checklists = cursor.execute("SELECT id, project_id, title FROM checklists").fetchall()
        for c in checklists:
            print(c)
    except Exception as e:
        print(f"Checklists table error: {e}")
