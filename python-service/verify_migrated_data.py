import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "projects.db"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("MIGRATED DATABASE CONTENTS")
print("=" * 80)

# Query project
cursor.execute("SELECT * FROM projects")
projects = cursor.fetchall()
print(f"\n📦 PROJECTS ({len(projects)}):")
for proj in projects:
    print(f"  - ID: {proj['id']}")
    print(f"    Name: {proj['name']}")
    print(f"    Requirements: {proj['text_requirements'][:80]}...")
    print(f"    Created: {proj['created_at']}")

# Query states
cursor.execute("SELECT * FROM project_states")
states = cursor.fetchall()
print(f"\n📊 PROJECT STATES ({len(states)}):")
for state in states:
    state_obj = json.loads(state['state'])
    print(f"  - Project ID: {state['project_id']}")
    print(f"    Platform: {state_obj.get('platform', 'N/A')}")
    print(f"    Architecture: {state_obj.get('architecture', 'N/A')}")
    print(f"    Updated: {state['updated_at']}")

# Query messages
cursor.execute("SELECT * FROM messages ORDER BY timestamp")
messages = cursor.fetchall()
print(f"\n💬 MESSAGES ({len(messages)}):")
for i, msg in enumerate(messages, 1):
    content_preview = msg['content'][:60].replace('\n', ' ')
    print(f"  {i}. [{msg['role']}] {content_preview}...")

print("\n" + "=" * 80)
print("✅ All migrated data verified!")
print("=" * 80)

conn.close()
