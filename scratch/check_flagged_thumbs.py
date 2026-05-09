import sys
import os
sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import B2Account, MediaItem
from backend.utils.b2_client import B2Client
import requests

db = SessionLocal()
try:
    a = db.query(B2Account).first()
    client = B2Client(a.key_id, a.application_key)
    items = db.query(MediaItem).filter(MediaItem.is_in_sorter == True).order_by(MediaItem.file_name).all()
    
    for m in items:
        thumb_url = client.get_download_url(f"{m.bucket_name}-thumbs", m.file_name, a.cloudflare_proxy_url)
        r = requests.get(thumb_url)
        print(f"{m.file_name} in {m.bucket_name}: Thumb Status {r.status_code}")
finally:
    db.close()
