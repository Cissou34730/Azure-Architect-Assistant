import sqlite3
import json

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT project_id, state FROM project_states").fetchall()

for p_id, state_str in rows:
    try:
        state = json.loads(state_str)
        waf = state.get('wafChecklist', {})
        items = waf.get('items', [])
        if isinstance(items, dict):
            item_count = len(items)
        else:
            item_count = len(items)
        
        if item_count > 0:
            print(f"Project {p_id}: {item_count} items in JSON")
        
        # Check normalized items
        ck_id = conn.execute("SELECT id FROM checklists WHERE project_id = ?", (p_id,)).fetchone()
        if ck_id:
            norm_items = conn.execute("SELECT count(*) FROM checklist_items WHERE checklist_id = ?", (ck_id[0],)).fetchone()[0]
            if norm_items > 0:
                print(f"Project {p_id}: {norm_items} items in SQL")
    except:
        pass
