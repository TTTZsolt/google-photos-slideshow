import sqlite3
conn = sqlite3.connect("photos_app.db")
cursor = conn.cursor()
cursor.execute("PRAGMA index_list('media_items');")
indices = cursor.fetchall()
print("Indices on media_items:")
for idx in indices:
    print(idx)
conn.close()
