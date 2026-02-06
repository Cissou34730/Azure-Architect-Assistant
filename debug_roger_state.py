import sqlite3
import json

db_path = '../../Azure-Architect-Assistant/backend/data/projects.db'
conn = sqlite3.connect(db_path)
row = conn.execute('SELECT project_id, state FROM project_states LIMIT 1').fetchone()

if row:
    project_id, state_str = row
    state = json.loads(state_str)
    print(f"Project ID: {project_id}")
    print(f"Keys in state: {list(state.keys())}")
    waf = state.get('wafChecklist', {})
    print(f"wafChecklist key type: {type(waf)}")
    if isinstance(waf, dict):
        print(f"wafChecklist items count: {len(waf.get('items', []))}")
    
    findings = state.get('findings', [])
    print(f"Findings count: {len(findings)}")
else:
    print("No project state found")
