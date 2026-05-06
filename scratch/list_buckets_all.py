from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client

db = SessionLocal()
acc = db.query(B2Account).filter(B2Account.is_active==True).first()
client = B2Client(acc.key_id, acc.application_key)

print("Listing all buckets:")
try:
    for bucket in client.b2_api.list_buckets():
        print(f" - {bucket.name}")
except Exception as e:
    print(f"Error: {e}")

db.close()
