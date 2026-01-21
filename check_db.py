import sqlite3
import sys

def check_database(db_path, db_name):
    print(f"\n{'='*60}")
    print(f"Checking {db_name}")
    print('='*60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print(f"⚠️  No tables found in {db_name}")
            return
        
        print(f"\nTables found: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            
            print(f"\n📊 {table_name}: {count} rows")
            if rows:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"   Columns: {', '.join(columns)}")
                print(f"   Sample: {len(rows)} rows")
            else:
                print(f"   ❌ Empty table")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking {db_name}: {e}")

if __name__ == "__main__":
    check_database("backend/data/projects.db", "Projects Database")
    check_database("backend/data/ingestion.db", "Ingestion Database")

