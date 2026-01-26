import sqlite3
import os

db_path = "photos_app.db"
if not os.path.exists(db_path):
    db_path = "backend/photos_app.db" # check subfolder too

print(f"Migrating database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add sync_status
    try:
        cursor.execute("ALTER TABLE b2_accounts ADD COLUMN sync_status TEXT DEFAULT 'Idle';")
        print("Column 'sync_status' added.")
    except sqlite3.OperationalError:
        print("Column 'sync_status' already exists.")

    # Add sync_count
    try:
        cursor.execute("ALTER TABLE b2_accounts ADD COLUMN sync_count INTEGER DEFAULT 0;")
        print("Column 'sync_count' added.")
    except sqlite3.OperationalError:
        print("Column 'sync_count' already exists.")

    conn.commit()
    conn.close()
    print("Migration successful.")
except Exception as e:
    print(f"Migration error: {e}")
