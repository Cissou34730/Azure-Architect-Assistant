import sqlite3
import json

import sqlite3
import os

dbs = [
    'backend/data/projects.db',
    'Azure-Architect-Assistant/backend/data/projects.db',
    'C:/Users/cyril.beurier/code/Azure-Architect-Assistant/backend/data/projects.db'
]

for db in dbs:
    if not os.path.exists(db):
        continue
    conn = sqlite3.connect(db)
    project = conn.execute("SELECT id, name FROM projects WHERE name LIKE '%Roger%'").fetchone()
    if project:
        p_id = project[0]
        state_row = conn.execute("SELECT state FROM project_states WHERE project_id=?", (p_id,)).fetchone()
        if state_row:
            state = json.loads(state_row[0])
            print(f"--- Roger State in {db} ---")
            print(f"WAF Checklist from state: {state.get('wafChecklist', 'MISSING')}")
            coverage = state.get('mindMapCoverage', {})
            topics = coverage.get('topics', {})
            print(f"MindMap Coverage: {coverage.get('version', 'N/A')}, topics: {len(topics)}")
            statuses = {}
            for t, d in topics.items():
                s = d.get('status', 'missing')
                statuses[s] = statuses.get(s, 0) + 1
            print(f"Statuses: {statuses}")
    conn.close()
