import sqlite3
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)

p_name = 'Legacy Project'
p_id_row = conn.execute("SELECT id FROM projects WHERE name=?", (p_name,)).fetchone()
if p_id_row:
    p_id = p_id_row[0]
    print(f"Project: {p_name} (ID: {p_id})")
    
    checklist = conn.execute("SELECT id, template_slug, title, completion_percentage FROM checklists WHERE project_id=?", (p_id,)).fetchone()
    if checklist:
        print(f"Checklist: {checklist}")
        items = conn.execute("SELECT id, title, pillar FROM checklist_items WHERE checklist_id=?", (checklist[0],)).fetchall()
        print(f"Items found: {len(items)}")
        for it in items[:2]:
            print(f"  Item: {it}")
            
        evals = conn.execute("SELECT id, item_id, status FROM checklist_item_evaluations WHERE project_id=?", (p_id,)).fetchall()
        print(f"Evaluations found: {len(evals)}")
        for ev in evals[:2]:
            print(f"  Eval: {ev}")
    else:
        print("No checklist found in SQL.")
else:
    print(f"Project {p_name} not found.")

conn.close()
