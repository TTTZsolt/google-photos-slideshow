import logging
from sqlalchemy.orm import Session
from sqlalchemy import delete, func
from .database import SessionLocal
from .models import MediaItem, B2Account
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Backblaze B2 Sync Worker

def sync_b2_worker(b2_account_id: int):
    db = SessionLocal()
    try:
        from .utils.b2_client import B2Client
        
        b2_account = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
        if not b2_account:
            logger.error(f"B2 Account {b2_account_id} not found")
            return

        logger.info(f"Starting B2 sync for bucket: {b2_account.bucket_name}")
        client = B2Client(b2_account.key_id, b2_account.application_key)
        
        # Simple implementation: Full re-sync (delete existing for this bucket)
        db.execute(delete(MediaItem).where(MediaItem.b2_account_id == b2_account_id))
        db.commit()

        count = 0
        for file_version in client.list_files(b2_account.bucket_name):
            # Filter for images
            mime = file_version.content_type
            file_name = file_version.file_name
            
            # Check extension if mime type is generic or missing
            ext = file_name.lower().split('.')[-1]
            if mime and not mime.startswith('image/'):
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    continue

            media_item = MediaItem(
                id=file_version.id_,
                b2_account_id=b2_account_id,
                file_name=file_name,
                mime_type=mime if (mime and mime.startswith('image/')) else f"image/{ext}",
                size=file_version.size,
                creation_time=datetime.fromtimestamp(file_version.upload_timestamp / 1000)
            )
            db.merge(media_item)
            count += 1
            if count % 100 == 0:
                db.commit()
                logger.info(f"Indexed {count} files from {b2_account.bucket_name}...")
        
        b2_account.last_synced_at = func.now()
        db.commit()
        logger.info(f"Finished sync for {b2_account.bucket_name}. Total items: {count}")

    except Exception as e:
        logger.exception(f"Error syncing B2 account {b2_account_id}: {e}")
    finally:
        db.close()

def sync_all_accounts_worker():
    db = SessionLocal()
    try:
        # Syncing B2 accounts
        b2_accounts = db.query(B2Account).filter(B2Account.is_active == True).all()
        for b2_acc in b2_accounts:
            sync_b2_worker(b2_acc.id)
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_accounts_worker()
