import sqlite3
import os

db_path = "photos_app.db"
print(f"Checking {db_path}...")
if not os.path.exists(db_path):
    print("DB file not found!")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        print(f"Integrity result: {result}")
        
        cursor.execute("SELECT count(*) FROM b2_accounts;")
        print(f"B2 accounts count: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT count(*) FROM media_items;")
        print(f"Media items count: {cursor.fetchone()[0]}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking DB: {e}")
