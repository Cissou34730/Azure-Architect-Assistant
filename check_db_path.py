import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.projects_database import DB_PATH
    print(f"DEBUG: Resolved DB_PATH = {DB_PATH.absolute()}")
    
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM projects")
    count = cursor.fetchone()[0]
    print(f"DEBUG: Project count in that DB = {count}")
    
    cursor.execute("SELECT name FROM projects")
    names = [r[0] for r in cursor.fetchall()]
    print(f"DEBUG: Project names = {names}")
    
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
