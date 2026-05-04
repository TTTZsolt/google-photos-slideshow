from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client

db = SessionLocal()
acc = db.query(B2Account).filter(B2Account.is_active==True).first()
client = B2Client(acc.key_id, acc.application_key)

file_name = "2009/02/reka-uszoiskola/imga0465.jpg"
thumb_buckets = ["forras-thumbs", "kepek01-thumbs", "kepek02-thumbs", "torles-elott-thumbs"]

for bucket_name in thumb_buckets:
    print(f"Checking {bucket_name}...")
    try:
        bucket = client.b2_api.get_bucket_by_name(bucket_name)
        bucket.get_file_info_by_name(file_name)
        print(f"  FOUND in {bucket_name}!")
    except:
        print(f"  Not found in {bucket_name}")

db.close()
