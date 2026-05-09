import sys
import os
sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import B2Account, MediaItem
from backend.utils.b2_client import B2Client

db = SessionLocal()
try:
    a = db.query(B2Account).first()
    client = B2Client(a.key_id, a.application_key)
    filename = '2007/12/ho-ha-ho/imga0293.jpg'
    
    print(f"Checking {filename}...")
    
    # Check forras
    try:
        b_forras = client.b2_api.get_bucket_by_name('forras')
        info = b_forras.get_file_info_by_name(filename)
        print(f"PHYSICALLY in forras: {info.id_}")
    except:
        print("NOT in forras physically")
        
    # Check torles-elott
    try:
        b_trash = client.b2_api.get_bucket_by_name('torles-elott')
        info = b_trash.get_file_info_by_name(filename)
        print(f"PHYSICALLY in torles-elott: {info.id_}")
    except:
        print("NOT in torles-elott physically")
        
    # Check DB
    items = db.query(MediaItem).filter(MediaItem.file_name == filename).all()
    print(f"DB records: {len(items)}")
    for m in items:
        print(f"  - ID: {m.id[:8]}, Bucket: {m.bucket_name}")

finally:
    db.close()
