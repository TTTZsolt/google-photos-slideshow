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
    ).filter(MediaClassification.is_deleted == True).group_by(MediaClassification.file_name)
    
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
        file_name_search = file_id.replace("virtual-", "", 1) if file_id.startswith("virtual-") else None
        mc = db.query(MediaClassification).filter(MediaClassification.file_name == file_name_search).first()
        if mc:
            mc.is_deleted = False
            mc.category = None
            
            # Also try to flag the actual MediaItem if it exists
            mi_real = db.query(MediaItem).filter(MediaItem.file_name == mc.file_name).first()
            if mi_real:
                mi_real.is_in_sorter = True
                
            db.commit()
            return {"status": "ok", "message": f"{mc.file_name} visszaállítva (adatbázis szinten)."}
        
        raise HTTPException(status_code=404, detail="Fájl nem található.")

    b2_acc = db.query(B2Account).filter(B2Account.id == mi.b2_account_id).first()
    if not b2_acc or not b2_acc.source_bucket_name:
        raise HTTPException(status_code=500, detail="Hiányzó forrás vödör konfiguráció.")

    try:
        client = B2Client(b2_acc.key_id, b2_acc.application_key)
        
        # 1. Move physically in B2 (Original + Thumb)
        new_version = client.move_file(mi.bucket_name, b2_acc.source_bucket_name, mi.file_name)
        try:
            client.move_file(f"{mi.bucket_name}-thumbs", f"{b2_acc.source_bucket_name}-thumbs", mi.file_name)
        except Exception as th_err:
            logger.warning(f"Could not restore thumbnail for {mi.file_name}: {th_err}")
        
        # 2. Update MediaItem entry
        mi.bucket_name = b2_acc.source_bucket_name
        mi.id = new_version.id_
        mi.is_in_sorter = True
        
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

    # 1. Identify items to delete
    query = db.query(MediaClassification, MediaItem).outerjoin(
        MediaItem, MediaItem.file_name == MediaClassification.file_name
    ).filter(MediaClassification.is_deleted == True)
    
    results = query.all()
    if not results:
        return {"status": "ok", "message": "A lomtár már üres."}

    # Prepare data for background task
    items_to_delete = []
    for mc, mi in results:
        items_to_delete.append({
            "file_name": mc.file_name,
            "file_id": mi.id if mi else None,
            "bucket_name": mi.bucket_name if mi else b2_acc.trash_bucket_name
        })

    # 2. IMMEDIATE DB CLEANUP (Main thread)
    # This ensures the UI sees the empty state right away
    for mc, mi in results:
        db.delete(mc)
        if mi:
            db.delete(mi)
    db.commit()

    # Convert to primitives for background task safety
    key_id = b2_acc.key_id
    app_key = b2_acc.application_key

    def perform_physical_delete(b2_key: str, b2_secret: str, items: List[dict]):
        client = B2Client(b2_key, b2_secret)
        for item in items:
            file_name = item["file_name"]
            file_id = item["file_id"]
            current_bucket = item["bucket_name"]

            try:
                # Skip B2 if ID is virtual
                if file_id and str(file_id).startswith('repair-'):
                    continue

                # Fetch missing B2 ID if needed
                if not file_id:
                    try:
                        trash_bucket = client.b2_api.get_bucket_by_name(current_bucket)
                        file_info = trash_bucket.get_file_info_by_name(file_name)
                        file_id = file_info.id_
                    except:
                        pass

                # Delete B2 file
                if file_id:
                    try:
                        client.delete_file_version(current_bucket, file_name, file_id)
                        # Also try to delete thumbnail
                        try:
                            client.delete_file_version(f"{current_bucket}-thumbs", file_name, "")
                        except:
                            pass
                    except Exception as b2_err:
                        logger.warning(f"B2 Delete error for {file_name}: {b2_err}")
            except Exception as e:
                logger.error(f"Failed background trash delete for {file_name}: {e}")

    background_tasks.add_task(perform_physical_delete, key_id, app_key, items_to_delete)
    return {"status": "ok", "message": f"{len(items_to_delete)} elem törlése megkezdődött."}


