import sqlite3
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)
evals = conn.execute("SELECT p.name, count(e.id) FROM projects p JOIN checklist_item_evaluations e ON p.id = e.project_id GROUP BY p.name").fetchall()
print(f"Projects with evaluations: {evals}")

# Also check for orphaned evaluations
all_evals = conn.execute("SELECT count(*) FROM checklist_item_evaluations").fetchone()[0]
mapped_evals = sum(e[1] for e in evals)
print(f"Total evals: {all_evals}, Mapped evals: {mapped_evals}")

if all_evals > mapped_evals:
    orphans = conn.execute("SELECT project_id, count(*) FROM checklist_item_evaluations WHERE project_id NOT IN (SELECT id FROM projects) GROUP BY project_id").fetchall()
    print(f"Orphaned evals by project_id: {orphans}")

conn.close()
