import sqlite3
db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)
res = conn.execute("SELECT template_slug, id FROM checklists WHERE project_id = 'df1a9feb-a194-4c9e-b35b-def938f7f1af'").fetchall()
print(f"Checklists for Roger: {res}")

for slug, ck_id in res:
    items = conn.execute("SELECT count(*) FROM checklist_items WHERE checklist_id = ?", (ck_id,)).fetchone()[0]
    print(f"Items for {slug}: {items}")
    evals = conn.execute("SELECT count(*) FROM checklist_item_evaluations WHERE item_id IN (SELECT id FROM checklist_items WHERE checklist_id = ?)", (ck_id,)).fetchall()
    print(f"Evaluations for {slug}: {evals}")
