from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import SessionLocal
from ..models import MediaItem, MediaClassification, B2Account
from ..slideshow import controller
from ..utils.b2_client import B2Client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/trash")
def get_trash_items(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Returns a paginated list of items currently in the trash."""
    # Using outerjoin to ensure we see items even if MediaItem record is missing
    query = db.query(MediaClassification, MediaItem).outerjoin(
        MediaItem, MediaClassification.file_name == MediaItem.file_name
    ).filter(MediaClassification.is_deleted == True)
    
    # Sort by date descending (assuming mc.updated_at is a good indicator)
    from sqlalchemy import desc
    query = query.order_by(desc(MediaClassification.updated_at))
    
    results = query.offset(offset).limit(limit).all()

    items = []
    # Get active account for base URL / auth
    b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_acc:
        return []

    client = B2Client(b2_acc.key_id, b2_acc.application_key)

    for mc, mi in results:
        # Generate temporary download URL for preview
        url = None
        thumb_url = None
        bucket_name = mi.bucket_name if mi else b2_acc.trash_bucket_name
        file_name = mc.file_name
        
        if bucket_name and file_name:
            try:
                # Original URL
                url = client.get_download_url(bucket_name, file_name, b2_acc.cloudflare_proxy_url)
                # Thumbnail URL (from the -thumbs bucket)
                thumb_url = client.get_download_url(f"{bucket_name}-thumbs", file_name, b2_acc.cloudflare_proxy_url)
            except Exception as e:
                logger.warning(f"Could not generate trash URL for {file_name}: {e}")

        items.append({
            "id": mi.id if mi else f"virtual-{mc.file_name}",
            "file_name": mc.file_name,
            "bucket_name": bucket_name,
            "url": url,
            "thumb_url": thumb_url,
            "updated_at": mc.updated_at
        })
    
    return items

@router.get("/api/trash/count")
def get_trash_count(db: Session = Depends(get_db)):
    """Returns the number of items in the trash."""
    count = db.query(MediaClassification).filter(MediaClassification.is_deleted == True).count()
    return {"count": count}

@router.post("/api/trash/restore/{file_id}")
def restore_from_trash(file_id: str, db: Session = Depends(get_db)):
    """Moves a file back from trash to the source bucket."""
    # Special handling for virtual IDs
    if file_id.startswith("virtual-"):
        file_name = file_id.replace("virtual-", "", 1)
        mi = db.query(MediaItem).filter(MediaItem.file_name == file_name).first()
    else:
        mi = db.query(MediaItem).filter(MediaItem.id == file_id).first()

    if not mi:
        # If it's pure virtual (no MediaItem at all), we might need to find it by name in Classification
        # and create a temporary B2 move if possible, but let's assume MediaItem usually exists
        # or we just update the classification and wait for next sync.
        # But for now, let's try to restore by file_name if mi is missing
        file_name_search = file_id.replace("virtual-", "", 1) if file_id.startswith("virtual-") else None
        mc = db.query(MediaClassification).filter(MediaClassification.file_name == file_name_search).first()
        if mc:
            mc.is_deleted = False
            mc.category = None
            db.commit()
            return {"status": "ok", "message": f"{mc.file_name} visszaállítva (adatbázis szinten)."}
        
        raise HTTPException(status_code=404, detail="Fájl nem található.")

    b2_acc = db.query(B2Account).filter(B2Account.id == mi.b2_account_id).first()
    if not b2_acc or not b2_acc.source_bucket_name:
        raise HTTPException(status_code=500, detail="Hiányzó forrás vödör konfiguráció.")

    try:
        client = B2Client(b2_acc.key_id, b2_acc.application_key)
        
        # 1. Move physically in B2
        new_version = client.move_file(mi.bucket_name, b2_acc.source_bucket_name, mi.file_name)
        
        # 2. Update MediaItem entry
        mi.bucket_name = b2_acc.source_bucket_name
        mi.id = new_version.id_
        
        # 3. Update Classification
        mc = db.query(MediaClassification).filter(MediaClassification.file_name == mi.file_name).first()
        if mc:
            mc.is_deleted = False
            mc.category = None # Put back to unclassified
            
        db.commit()
        return {"status": "ok", "message": f"{mi.file_name} visszaállítva a forrásba."}
    except Exception as e:
        db.rollback()
        logger.exception("Restore error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/trash/empty")
def empty_trash(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Starts a background task to physically delete all items in trash."""
    # Fetch credentials in the request thread
    b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_acc or not b2_acc.trash_bucket_name:
        raise HTTPException(status_code=400, detail="Nincs Lomtár vödör beállítva.")

    # Convert to primitives for background task safety (avoid DetachedInstanceError)
    key_id = b2_acc.key_id
    app_key = b2_acc.application_key
    trash_bucket_name = b2_acc.trash_bucket_name

    def perform_empty(b2_key: str, b2_secret: str, bucket_name: str):
        # Independent session for background
        from ..database import SessionLocal
        local_db = SessionLocal()
        try:
            # Query items to kill
            query = local_db.query(MediaClassification, MediaItem).outerjoin(
                MediaItem, MediaItem.file_name == MediaClassification.file_name
            ).filter(MediaClassification.is_deleted == True)
            
            results = query.all()
            logger.info(f"Empty Trash: Found {len(results)} items to delete.")

            client = B2Client(b2_key, b2_secret)
            trash_bucket = client.b2_api.get_bucket_by_name(bucket_name)
            
            for mc, mi in results:
                file_name = mc.file_name
                file_id = mi.id if mi else None
                current_bucket = mi.bucket_name if mi else bucket_name

                try:
                    # 1. Skip B2 if ID is virtual (repair-*)
                    skip_b2 = False
                    if file_id and str(file_id).startswith('repair-'):
                        logger.info(f"Skipping B2 delete for virtual ID: {file_id}")
                        skip_b2 = True

                    # 2. Fetch missing B2 ID if needed (only if not skipping)
                    if not file_id and not skip_b2:
                        logger.info(f"Fetching B2 ID for virtual trash item: {file_name}")
                        try:
                            file_info = trash_bucket.get_file_info_by_name(file_name)
                            file_id = file_info.id_
                        except Exception as b2_id_err:
                            logger.warning(f"Could not find {file_name} in B2 trash bucket: {b2_id_err}")
                            # Continue to DB cleanup anyway

                    # 3. Delete B2 file
                    if file_id and not skip_b2:
                        try:
                            client.delete_file_version(current_bucket, file_name, file_id)
                            # V14.3.3: Also try to delete thumbnail
                            try:
                                thumb_bucket = f"{current_bucket}-thumbs"
                                client.delete_file_version(thumb_bucket, file_name, "") # Use empty ID for listing/finding if possible, or just skip if fail
                            except:
                                pass # Thumbs might not exist, that's fine
                        except Exception as b2_del_err:
                            err_msg = str(b2_del_err).lower()
                            # If file not present or bad id, it's effectively "deleted"
                            if "not found" in err_msg or "not present" in err_msg or "bad" in err_msg:
                                logger.info(f"File already gone from B2 or ID invalid: {file_name}")
                            else:
                                raise b2_del_err # Rethrow critical errors

                    # 4. DB Cleanup
                    local_db.delete(mc)
                    if mi:
                        local_db.delete(mi)
                    
                    local_db.commit()
                    logger.info(f"Trash finalized for {file_name}")
                except Exception as e:
                    logger.error(f"Failed to process trash item {file_name}: {e}")
                    local_db.rollback()
        finally:
            local_db.close()

    background_tasks.add_task(perform_empty, key_id, app_key, trash_bucket_name)
    return {"status": "started", "message": "Lomtár ürítése megkezdődött a háttérben."}


