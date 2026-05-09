import sys
import os
sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import MediaItem, B2Account, MediaClassification
from sqlalchemy import or_, and_

db = SessionLocal()
try:
    b2 = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2:
        print("No active B2 account")
    else:
        print(f"Source bucket: {b2.source_bucket_name}")
        print(f"Main bucket: {b2.bucket_name}")
        
        q = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            or_(
                MediaItem.is_in_sorter == True,
                MediaItem.bucket_name == b2.source_bucket_name
            )
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(MediaClassification.category == None, MediaClassification.is_deleted == False)
            )
        )
        
        count = q.count()
        print(f"Total matching items: {count}")
        
        first = q.order_by(MediaItem.file_name.asc()).first()
        if first:
            print(f"First item: {first.file_name} in {first.bucket_name}")
        else:
            print("No items found matching criteria")
finally:
    db.close()
