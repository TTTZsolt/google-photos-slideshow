import sqlite3
import os

db_path = "photos_app.db"
if not os.path.exists(db_path):
    if os.path.exists("backend/photos_app.db"):
        db_path = "backend/photos_app.db"

print(f"Migrating database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. B2Account additions
    for col in ["source_bucket_name", "trash_bucket_name"]:
        try:
            cursor.execute(f"ALTER TABLE b2_accounts ADD COLUMN {col} TEXT;")
            print(f"Column '{col}' added to b2_accounts.")
        except sqlite3.OperationalError:
            print(f"Column '{col}' already exists in b2_accounts.")

    # 2. MediaItem additions
    try:
        cursor.execute("ALTER TABLE media_items ADD COLUMN bucket_name TEXT;")
        print("Column 'bucket_name' added to media_items.")
    except sqlite3.OperationalError:
        print("Column 'bucket_name' already exists in media_items.")

    # 3. Create MediaClassification table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_classifications (
                file_name TEXT PRIMARY KEY,
                category TEXT,
                is_deleted BOOLEAN DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Table 'media_classifications' created.")
    except Exception as e:
        print(f"Error creating media_classifications: {e}")

    conn.commit()
    conn.close()
    print("Migration successful.")
except Exception as e:
    print(f"Migration error: {e}")
