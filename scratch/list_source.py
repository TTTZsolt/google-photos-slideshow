from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client

db = SessionLocal()
acc = db.query(B2Account).filter(B2Account.is_active==True).first()
client = B2Client(acc.key_id, acc.application_key)

bucket_name = "forras"
print(f"Listing files in {bucket_name}:")
try:
    bucket = client.b2_api.get_bucket_by_name(bucket_name)
    for file_version, folder_name in bucket.ls(latest_only=True, recursive=True):
        print(f" - {file_version.file_name}")
except Exception as e:
    print(f"Error: {e}")

db.close()
