from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client

db = SessionLocal()
acc = db.query(B2Account).filter(B2Account.is_active==True).first()
client = B2Client(acc.key_id, acc.application_key)

source_bucket = "forras"
target_bucket = "kepek02"

print(f"Repairing thumbnails: {target_bucket}-thumbs -> {source_bucket}-thumbs")

try:
    bucket = client.b2_api.get_bucket_by_name(source_bucket)
    for file_version, folder_name in bucket.ls(latest_only=True, recursive=True):
        file_name = file_version.file_name
        print(f"Checking thumb for {file_name}...")
        try:
            # Check if thumb is in target-thumbs
            client.move_file(f"{target_bucket}-thumbs", f"{source_bucket}-thumbs", file_name, file_info={})
            print(f"  SUCCESS: Moved thumb back for {file_name}")
        except:
            print(f"  No thumb found in {target_bucket}-thumbs or already in source.")

except Exception as e:
    print(f"Error: {e}")

db.close()
