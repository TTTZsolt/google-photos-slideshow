from backend.database import SessionLocal
from backend.models import B2Account
from backend.utils.b2_client import B2Client
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
acc = db.query(B2Account).filter(B2Account.is_active==True).first()
client = B2Client(acc.key_id, acc.application_key)

bucket_name = "forras-thumbs"
file_name = "2009/02/reka-uszoiskola/imga0465.jpg"

print(f"Checking {bucket_name}/{file_name}...")
try:
    bucket = client.b2_api.get_bucket_by_name(bucket_name)
    file_info = bucket.get_file_info_by_name(file_name)
    print(f"FOUND! ID: {file_info.id_}")
except Exception as e:
    print(f"NOT FOUND or Error: {e}")

db.close()
