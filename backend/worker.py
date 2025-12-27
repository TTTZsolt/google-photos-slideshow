import logging
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Account, MediaItem
from .auth import get_credentials_for_account
from .utils.google_photos import GooglePhotosClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_account_worker(account_id: int):
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            logger.error(f"Account {account_id} not found")
            return

        logger.info(f"Starting sync for account: {account.email}")
        
        creds = get_credentials_for_account(db, account_id)
        if not creds:
            logger.error(f"Could not get credentials for account {account_id}")
            return
        logger.info(f"Credentials scopes object: {creds.scopes}")

        # DEBUG: Check actual scopes via Google API
        try:
            import requests
            token_info = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={creds.token}").json()
            logger.info(f"DEBUG: Token Inspector response: {token_info}")
        except Exception as e:
            logger.error(f"DEBUG: Failed to inspect token: {e}")

        client = GooglePhotosClient(creds)
        
        # DEBUG: Try listing albums to check API access
        try:
            logger.info("DEBUG: Testing Access with list_albums...")
            albums = client.service.albums().list(pageSize=1).execute()
            logger.info(f"DEBUG: Albums response: {albums}")
        except Exception as e:
            logger.error(f"DEBUG: Albums list failed: {e}")

        count = 0
        batch = []
        BATCH_SIZE = 100

        for item in client.list_media_items():
            # Only index photos (skip videos if needed, but requirements said 'media items')
            # Assuming we want everything.
            
            media_item = MediaItem(
                id=item['id'],
                account_id=account.id,
                base_url=item['baseUrl'],
                mime_type=item.get('mimeType'),
                filename=item.get('filename'),
                creation_time=datetime.fromisoformat(item['mediaMetadata']['creationTime'].replace('Z', '+00:00')) if 'mediaMetadata' in item and 'creationTime' in item['mediaMetadata'] else None
            )
            
            # Upsert logic (simplified: merge)
            # In SQLAlchemy, merge checks primary key.
            batch.append(media_item)
            
            if len(batch) >= BATCH_SIZE:
                _save_batch(db, batch)
                count += len(batch)
                batch = []
                logger.info(f"Synced {count} items for {account.email}")

        if batch:
            _save_batch(db, batch)
            count += len(batch)
        
        account.last_synced_at = datetime.now()
        db.commit()
        logger.info(f"Finished sync for {account.email}. Total items: {count}")

    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {e}")
    finally:
        db.close()

def _save_batch(db: Session, items: list[MediaItem]):
    for item in items:
        db.merge(item)
    db.commit()

def sync_all_accounts_worker():
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        for account in accounts:
            sync_account_worker(account.id)
    finally:
        db.close()

if __name__ == "__main__":
    # Allow running as a script
    sync_all_accounts_worker()
