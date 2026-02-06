import sqlite3
import os
from pathlib import Path

def scan_db(db_path):
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get count of projects
        cursor.execute("SELECT count(*) FROM projects")
        count = cursor.fetchone()[0]
        
        # Get project names
        cursor.execute("SELECT name FROM projects")
        names = [row[0] for row in cursor.fetchall()]
        
        # Get count of checklist entries if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checklists'")
        has_checklists = cursor.fetchone() is not None
        checklist_count = 0
        if has_checklists:
            cursor.execute("SELECT count(*) FROM checklists")
            checklist_count = cursor.fetchone()[0]
            
        conn.close()
        return {
            "count": count,
            "names": names,
            "checklist_count": checklist_count
        }
    except Exception as e:
        return f"Error: {str(e)}"

backup_dir = Path("../Azure-Architect-Assistant/backups")
if backup_dir.exists():
    for folder in sorted(backup_dir.iterdir()):
        if folder.is_dir():
            db_path = folder / "projects.db"
            result = scan_db(db_path)
            if result:
                print(f"Folder: {folder.name}")
                print(f"  Projects count: {result['count']}")
                print(f"  Project names: {result['names']}")
                print(f"  Checklists count: {result['checklist_count']}")
                print("-" * 20)
else:
    print(f"Directory {backup_dir} not found")
