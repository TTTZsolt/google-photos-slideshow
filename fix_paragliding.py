import sqlite3
import os

def fix_categories():
    db_path = "photos_app.db"
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Rename the definition if it has the trailing dash
    cursor.execute("UPDATE category_definitions SET name = 'sikloernyo', display_name = 'Siklóernyő' WHERE name = 'sikloernyo-';")
    if cursor.rowcount > 0:
        print("Updated category definition: 'sikloernyo-' -> 'sikloernyo'")

    # 2. Also fix display name if it has a trailing space
    cursor.execute("UPDATE category_definitions SET display_name = 'Siklóernyő' WHERE display_name = 'Siklóernyő ';")
    
    # 3. Ensure media_classifications with 'sikloernyo-' are moved to 'sikloernyo'
    cursor.execute("UPDATE media_classifications SET category = 'sikloernyo' WHERE category = 'sikloernyo-';")
    if cursor.rowcount > 0:
        print(f"Updated {cursor.rowcount} images from 'sikloernyo-' to 'sikloernyo'")

    conn.commit()
    conn.close()
    print("Optimization finished.")

if __name__ == "__main__":
    fix_categories()
