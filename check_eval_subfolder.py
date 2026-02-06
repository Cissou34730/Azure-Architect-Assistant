import sqlite3
import os

db_path = 'Azure-Architect-Assistant/backend/data/projects.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    evals = conn.execute("SELECT p.name, count(e.id) FROM projects p JOIN checklist_item_evaluations e ON p.id = e.project_id GROUP BY p.name").fetchall()
    print(f"Projects with evaluations in {db_path}: {evals}")
    conn.close()
else:
    print(f"Path not found: {db_path}")
