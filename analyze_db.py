import sqlite3
from pathlib import Path
from datetime import datetime

def analyze_db_changes():
    print("="*70)
    print("DATABASE CHANGE ANALYSIS")
    print("="*70)
    
    dbs = [
        ("Projects DB", "backend/data/projects.db"),
        ("Ingestion DB", "backend/data/ingestion.db")
    ]
    
    for name, path in dbs:
        print(f"\n{'='*70}")
        print(f"{name}: {path}")
        print('='*70)
        
        if not Path(path).exists():
            print(f"❌ File does not exist!")
            continue
            
        # File stats
        stat = Path(path).stat()
        print(f"\n📁 File Info:")
        print(f"  Size: {stat.st_size / 1024:.2f} KB")
        print(f"  Modified: {datetime.fromtimestamp(stat.st_mtime)}")
        print(f"  Created: {datetime.fromtimestamp(stat.st_ctime)}")
        
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            
            print(f"\n📊 Tables ({len(tables)}):")
            
            total_rows = 0
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_rows += count
                
                # Get last modified date if possible
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    cols = cursor.fetchall()
                    
                    # Look for timestamp columns
                    timestamp_cols = [c[1] for c in cols if 'time' in c[1].lower() or 'date' in c[1].lower() or 'updated' in c[1].lower()]
                    
                    last_mod = "N/A"
                    if timestamp_cols and count > 0:
                        try:
                            cursor.execute(f"SELECT MAX({timestamp_cols[0]}) FROM {table}")
                            result = cursor.fetchone()[0]
                            if result:
                                last_mod = result
                        except:
                            pass
                    
                    status = "✅ Has data" if count > 0 else "❌ Empty"
                    print(f"  {table:30s} {count:6d} rows  {status}  Last: {last_mod}")
                except Exception as e:
                    print(f"  {table:30s} {count:6d} rows  (error getting details)")
            
            print(f"\n📈 Total rows across all tables: {total_rows}")
            
            if total_rows == 0:
                print("\n⚠️  WARNING: Database has structure but NO DATA")
                print("   This suggests:")
                print("   1. Database was recently recreated/reset")
                print("   2. Data was deleted")
                print("   3. This is a fresh installation")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_db_changes()
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print("\n1. Check git history for database changes:")
    print("   git log --all --full-history -- backend/data/*.db")
    print("\n2. Check if databases are in .gitignore (they should be)")
    print("\n3. Look for OneDrive sync conflicts (common issue)")
    print("\n4. Check if migration scripts were run recently")
