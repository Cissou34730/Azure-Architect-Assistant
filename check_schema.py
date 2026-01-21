import sqlite3

conn = sqlite3.connect('backend/data/ingestion.db')
c = conn.cursor()

# Check schema version
c.execute('SELECT version FROM ingestion_schema_version')
print('Current schema version:', c.fetchone()[0])

# Check if phase_status table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_phase_status'")
result = c.fetchone()
if result:
    print('\n✅ ingestion_phase_status table EXISTS')
    c.execute('PRAGMA table_info(ingestion_phase_status)')
    print('\nColumns:')
    for row in c.fetchall():
        print(f'  {row[1]} ({row[2]})')
else:
    print('\n❌ ingestion_phase_status table MISSING')

# Check ingestion_jobs structure
print('\n--- ingestion_jobs structure ---')
c.execute('PRAGMA table_info(ingestion_jobs)')
for row in c.fetchall():
    print(f'  {row[1]} ({row[2]})')

conn.close()

