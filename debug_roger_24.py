import sqlite3
import json
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
if not os.path.exists(db_path):
    print(f"File not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
row = conn.execute("SELECT id FROM projects WHERE name='Roger'").fetchone()

if row:
    # No state column in this DB's projects table
    print("Project found")
    
    # Check SQL tables for Roger
    p_id = conn.execute("SELECT id FROM projects WHERE name='Roger'").fetchone()[0]
    print(f"Roger ID: {p_id}")
    
    c_count = conn.execute("SELECT count(*) FROM checklists WHERE project_id=?", (p_id,)).fetchone()[0]
    print(f"Checklists in SQL for Roger: {c_count}")
    
    e_count = conn.execute("SELECT count(*) FROM checklist_item_evaluations WHERE project_id=?", (p_id,)).fetchone()[0]
    print(f"Evaluations in SQL for Roger: {e_count}")
    
    if e_count > 0:
        evals = conn.execute("SELECT status, count(*) FROM checklist_item_evaluations WHERE project_id=? GROUP BY status", (p_id,)).fetchall()
        print(f"Eval statuses: {evals}")
else:
    print("Roger project not found")

conn.close()
