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
    for col in ["source_bucket_name", "trash_bucket_name", "sync_total", "incoming_bucket_name"]:
        try:
            # Set INTEGER for sync_total, TEXT for others
            col_type = "INTEGER" if col == "sync_total" else "TEXT"
            cursor.execute(f"ALTER TABLE b2_accounts ADD COLUMN {col} {col_type};")
            print(f"Column '{col}' added to b2_accounts.")
            if col == "sync_total":
                cursor.execute("UPDATE b2_accounts SET sync_total = 0 WHERE sync_total IS NULL;")
                print("Set default 0 for sync_total.")
        except sqlite3.OperationalError:
            print(f"Column '{col}' already exists in b2_accounts.")
        
        # Ensure default values for existing rows
        if col == "sync_total":
            cursor.execute("UPDATE b2_accounts SET sync_total = 0 WHERE sync_total IS NULL;")
            cursor.execute("UPDATE b2_accounts SET sync_count = 0 WHERE sync_count IS NULL;")
            print("Verified default 0 for sync_total and sync_count.")

    # 2. MediaItem additions
    try:
        cursor.execute("ALTER TABLE media_items ADD COLUMN bucket_name TEXT;")
        print("Column 'bucket_name' added to media_items.")
    except sqlite3.OperationalError:
        print("Column 'bucket_name' already exists in media_items.")

    try:
        cursor.execute("ALTER TABLE media_items ADD COLUMN sha1 TEXT;")
        print("Column 'sha1' added to media_items.")
    except sqlite3.OperationalError:
        print("Column 'sha1' already exists in media_items.")

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

    # 4. Create DeletedContentHash table (tombstone for permanently emptied trash items)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deleted_content_hashes (
                sha1 TEXT PRIMARY KEY,
                last_known_file_name TEXT,
                deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            );
        """)
        print("Table 'deleted_content_hashes' created.")
    except Exception as e:
        print(f"Error creating deleted_content_hashes: {e}")

    conn.commit()
    try:
        cursor.execute("UPDATE category_definitions SET name = 'sikloernyo', display_name = 'Siklóernyő' WHERE name = 'sikloernyo-';")
        cursor.execute("UPDATE media_classifications SET category = 'sikloernyo' WHERE category = 'sikloernyo-';")
        conn.commit()
        print("Cleanup: Unified paragliding category names.")
    except Exception as e:
        print(f"Cleanup error: {e}")

    conn.close()
    print("Migration successful.")
except Exception as e:
    print(f"Migration error: {e}")
