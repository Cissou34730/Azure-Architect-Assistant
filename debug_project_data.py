import sqlite3
import json
import os

db_path = '../Azure-Architect-Assistant/backend/data/projects.db'

def inspect_project(project_id, name):
    print(f"--- Inspecting {name} ({project_id}) ---")
    conn = sqlite3.connect(db_path)
    try:
        # Check project_states
        row = conn.execute("SELECT state FROM project_states WHERE project_id=?", (project_id,)).fetchone()
        if row:
            state = json.loads(row[0])
            waf = state.get('wafChecklist', {})
            print(f"Legacy WAF Keys: {list(waf.keys())}")
            if waf:
                # Print the full waf structure
                print(f"Full WAF Structure: {json.dumps(waf, indent=2)}")
        else:
            print("No entry in project_states")

        # Check evaluations
        count = conn.execute("SELECT COUNT(*) FROM checklist_item_evaluations WHERE project_id=?", (project_id,)).fetchone()[0]
        print(f"SQL Evaluation Count: {count}")
    finally:
        conn.close()

# Roger
inspect_project('df1a9feb-a194-4c9e-b35b-def938f7f1af', 'Roger')
# Legacy Project
inspect_project('961ba7fd-7cb6-4f2e-a712-8d58d7464583', 'Legacy Project')
# Scenario A
inspect_project('df121233-8704-4456-a9ed-7d40173750da', 'Scenario A')
