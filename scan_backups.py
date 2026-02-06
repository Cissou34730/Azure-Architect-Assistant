import sqlite3
import os

backups_dir = 'backups'
for folder in sorted(os.listdir(backups_dir)):
    db_path = os.path.join(backups_dir, folder, 'projects.db')
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            print(f"Backup {folder} tables: {tables}")
            if 'projects' in tables:
                projects = conn.execute("SELECT id, name FROM projects").fetchall()
                print(f"  - {len(projects)} projects")
            conn.close()
        except Exception as e:
            print(f"Backup {folder}: Error {e}")
