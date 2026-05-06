import logging
from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    db = SessionLocal()
    acc = db.query(B2Account).filter(B2Account.is_active==True).first()
    if not acc:
        print("No active B2 account found.")
        return
    
    client = B2Client(acc.key_id, acc.application_key)
    
    # 1. kepek01 (Archive) -> add -eredeti
    archive_bucket = acc.archive_bucket_name or "kepek01"
    print(f"--- Processing {archive_bucket} (Adding -eredeti) ---")
    try:
        files = list(client.list_files(archive_bucket))
        for f in files:
            name = f.file_name
            if "-eredeti." not in name.lower():
                parts = name.rsplit('.', 1)
                new_name = f"{parts[0]}-eredeti.{parts[1]}" if len(parts)==2 else f"{name}-eredeti"
                print(f"Renaming {name} -> {new_name}")
                try:
                    client.move_file(archive_bucket, archive_bucket, name, dest_file_name=new_name)
                    # Try thumb too
                    try:
                        client.move_file(f"{archive_bucket}-thumbs", f"{archive_bucket}-thumbs", name, dest_file_name=new_name)
                    except: pass
                except Exception as e:
                    print(f"  Error renaming {name}: {e}")
    except Exception as e:
        print(f"Error listing {archive_bucket}: {e}")

    # 2. kepek02 (Main) -> remove -szerkesztett
    main_bucket = acc.bucket_name or "kepek02"
    print(f"\n--- Processing {main_bucket} (Removing -szerkesztett) ---")
    try:
        files = list(client.list_files(main_bucket))
        for f in files:
            name = f.file_name
            if "-szerkesztett." in name.lower():
                new_name = name.replace("-szerkesztett.", ".")
                print(f"Renaming {name} -> {new_name}")
                try:
                    client.move_file(main_bucket, main_bucket, name, dest_file_name=new_name)
                    # Try thumb too
                    try:
                        client.move_file(f"{main_bucket}-thumbs", f"{main_bucket}-thumbs", name, dest_file_name=new_name)
                    except: pass
                except Exception as e:
                    print(f"  Error renaming {name}: {e}")
    except Exception as e:
        print(f"Error listing {main_bucket}: {e}")

    db.close()
    print("\nMigration finished.")

if __name__ == "__main__":
    migrate()
