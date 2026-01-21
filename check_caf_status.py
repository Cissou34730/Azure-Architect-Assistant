import sqlite3

conn = sqlite3.connect('backend/data/ingestion.db')
cursor = conn.cursor()

# Get schema
cursor.execute("PRAGMA table_info(ingestion_jobs)")
print("ingestion_jobs columns:", [row[1] for row in cursor.fetchall()])

# Check ingestion_jobs table
cursor.execute('''
    SELECT * 
    FROM ingestion_jobs 
    WHERE kb_id = 'caf' 
    ORDER BY created_at DESC 
    LIMIT 3
''')
rows = cursor.fetchall()
print("\nCAF jobs:")
for row in rows:
    print(row)
conn.close()

