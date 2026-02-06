import sqlite3
import json
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)

# Find Roger's project_id
row = conn.execute("SELECT id FROM projects WHERE name='Roger'").fetchone()
if row:
    p_id = row[0]
    # Check project_states
    state_row = conn.execute("SELECT state FROM project_states WHERE project_id=?", (p_id,)).fetchone()
    if state_row:
        state = json.loads(state_row[0])
        print(f"Roger state keys: {list(state.keys())}")
        findings = state.get('findings', [])
        print(f"findings type: {type(findings)}")
        if isinstance(findings, list):
            print(f"findings length: {len(findings)}")
            if len(findings) > 0:
                print(f"First finding: {findings[0]}")
        elif isinstance(findings, dict):
            print(f"findings keys: {list(findings.keys())}")
    else:
        print("No project_state found for Roger")
else:
    print("Roger project not found")

conn.close()
