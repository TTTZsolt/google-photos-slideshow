
import sqlite3

db_path = "photos_app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Categories in media_classifications ---")
cursor.execute("SELECT category, COUNT(*) FROM media_classifications GROUP BY category")
for row in cursor.fetchall():
    print(f"Category: {row[0]}, Count: {row[1]}")

print("\n--- Searching for 'siklóernyő' specifically ---")
# Check with exact match and partial match
cursor.execute("SELECT category, COUNT(*) FROM media_classifications WHERE category LIKE '%sikl%' GROUP BY category")
for row in cursor.fetchall():
    print(f"Found match: {row[0]}, Count: {row[1]}")

print("\n--- Detailed Category Check (is_deleted status) ---")
cursor.execute("SELECT category, is_deleted, COUNT(*) FROM media_classifications WHERE category LIKE '%sikl%' GROUP BY category, is_deleted")
for row in cursor.fetchall():
    print(f"Category: {row[0]}, Is Deleted: {row[1]}, Count: {row[2]}")

print("\n--- All Unique Categories in media_classifications ---")
cursor.execute("SELECT DISTINCT category FROM media_classifications")
for row in cursor.fetchall():
    print(f"Category: {row[0]}")

conn.close()
