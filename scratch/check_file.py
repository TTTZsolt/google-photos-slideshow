import sys
import os
sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import MediaItem, MediaClassification

db = SessionLocal()
try:
    filename = '2015/06/london/p1160596.jpg'
    m = db.query(MediaItem).filter(MediaItem.file_name == filename).first()
    c = db.query(MediaClassification).filter(MediaClassification.file_name == filename).first()
    
    print(f"File: {filename}")
    if m:
        print(f"MediaItem: bucket={m.bucket_name}, is_in_sorter={m.is_in_sorter}")
    else:
        print("MediaItem: NOT FOUND")
        
    if c:
        print(f"Classification: category={c.category}, is_deleted={c.is_deleted}")
    else:
        print("Classification: NOT FOUND")
finally:
    db.close()
