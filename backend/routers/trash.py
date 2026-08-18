from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import SessionLocal
from ..models import MediaItem, MediaClassification, B2Account, DeletedContentHash
from ..slideshow import controller
from ..utils.b2_client import B2Client
import logging
import os
import csv

router = APIRouter()
logger = logging.getLogger(__name__)

# Megosztott CSV a Kepnezegeto projekt gyokereben - ezt olvassa be a kulon
# "Fenykep elokeszites BlackBlaze-be masolas" projektben elo takeout feltolto
# script, hogy ne toltsen fel ujra szandekosan torolt kepeket.
DELETED_SHA1_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "deleted_sha1_list.csv")

def append_deleted_sha1_csv(sha1: str, file_name: str, reason: str):
    file_exists = os.path.exists(DELETED_SHA1_CSV)
    with open(DELETED_SHA1_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["sha1", "last_known_file_name", "deleted_at", "reason"])
        from datetime import datetime, timezone
        writer.writerow([sha1, file_name, datetime.now(timezone.utc).isoformat(), reason])

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
    """Moves a file back from trash directly into the live bucket (Zero-Move:
    no longer bounces through the 'forras' staging bucket, which no longer
    has any active role in the architecture)."""
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
    if not b2_acc or not b2_acc.bucket_name:
        raise HTTPException(status_code=500, detail="Hiányzó éles vödör konfiguráció.")

    try:
        client = B2Client(b2_acc.key_id, b2_acc.application_key)

        # 1. Move physically in B2 (Original + Thumb) - directly into the live
        #    bucket, not via 'forras' (Zero-Move, l. mappazasi_algoritmus_specifikacio.md)
        new_version = client.move_file(mi.bucket_name, b2_acc.bucket_name, mi.file_name)
        try:
            client.move_file(f"{mi.bucket_name}-thumbs", f"{b2_acc.bucket_name}-thumbs", mi.file_name)
        except Exception as th_err:
            logger.warning(f"Could not restore thumbnail for {mi.file_name}: {th_err}")

        # 2. Update MediaItem entry
        mi.bucket_name = b2_acc.bucket_name
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
            "bucket_name": mi.bucket_name if mi else b2_acc.trash_bucket_name,
            "sha1": mi.sha1 if mi else None
        })

    # NOTE: DB rows are intentionally NOT deleted here up-front. The frontend
    # already clears the Trash view optimistically as soon as this request
    # succeeds (see trash.html), so there's no UX need to pre-clear the DB -
    # and doing so here used to mean a crash/hang partway through the
    # background loop below left the not-yet-processed items with no DB
    # record at all: physically still in the trash bucket, but invisible to
    # the app and absent from the tombstone list (so a Takeout re-upload
    # could resurrect them). Each item's DB rows are now removed only after
    # its own tombstone + physical delete attempt has run.

    # Convert to primitives for background task safety
    key_id = b2_acc.key_id
    app_key = b2_acc.application_key

    def perform_physical_delete(b2_key: str, b2_secret: str, items: List[dict]):
        client = B2Client(b2_key, b2_secret)
        tombstone_db = SessionLocal()
        try:
            for item in items:
                file_name = item["file_name"]
                file_id = item["file_id"]
                current_bucket = item["bucket_name"]
                sha1 = item.get("sha1")
                is_virtual = bool(file_id) and str(file_id).startswith('repair-')

                try:
                    if not is_virtual:
                        # Fetch missing B2 ID (and SHA1, if still missing) if needed
                        if not file_id or not sha1:
                            try:
                                trash_bucket = client.b2_api.get_bucket_by_name(current_bucket)
                                file_info = trash_bucket.get_file_info_by_name(file_name)
                                if not file_id:
                                    file_id = file_info.id_
                                if not sha1:
                                    sha1 = getattr(file_info, "content_sha1", None)
                            except:
                                pass

                        # Record the tombstone BEFORE the physical delete, so a crash
                        # mid-way still leaves the "don't re-upload this" record.
                        if sha1:
                            try:
                                existing = tombstone_db.query(DeletedContentHash).filter(DeletedContentHash.sha1 == sha1).first()
                                if not existing:
                                    tombstone_db.add(DeletedContentHash(sha1=sha1, last_known_file_name=file_name, reason="trash-empty"))
                                    tombstone_db.commit()
                                    append_deleted_sha1_csv(sha1, file_name, "trash-empty")
                            except Exception as tomb_err:
                                logger.error(f"Failed to record tombstone for {file_name}: {tomb_err}")
                                tombstone_db.rollback()

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

                    # Only now remove the DB rows for this item - after its own
                    # tombstone + physical delete attempt has actually run.
                    mc_row = tombstone_db.query(MediaClassification).filter(MediaClassification.file_name == file_name).first()
                    if mc_row:
                        tombstone_db.delete(mc_row)
                    mi_row = tombstone_db.query(MediaItem).filter(MediaItem.file_name == file_name).first()
                    if mi_row:
                        tombstone_db.delete(mi_row)
                    tombstone_db.commit()
                except Exception as e:
                    logger.error(f"Failed background trash delete for {file_name}: {e}")
                    tombstone_db.rollback()
        finally:
            tombstone_db.close()

    background_tasks.add_task(perform_physical_delete, key_id, app_key, items_to_delete)
    return {"status": "ok", "message": f"{len(items_to_delete)} elem törlése megkezdődött."}

@router.post("/api/trash/restore-all")
def restore_all_from_trash(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Restores all items from the trash directly into the live bucket
    (Zero-Move: no longer bounces through 'forras')."""
    b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_acc or not b2_acc.bucket_name:
        raise HTTPException(status_code=500, detail="Hiányzó éles vödör konfiguráció.")

    # 1. Identify items to restore
    query = db.query(MediaClassification, MediaItem).outerjoin(
        MediaItem, MediaItem.file_name == MediaClassification.file_name
    ).filter(MediaClassification.is_deleted == True)
    
    results = query.all()
    if not results:
        return {"status": "ok", "message": "A lomtár üres."}

    items_to_restore = []
    for mc, mi in results:
        items_to_restore.append({
            "file_name": mc.file_name,
            "mi_id": mi.id if mi else None,
            "current_bucket": mi.bucket_name if mi else b2_acc.trash_bucket_name
        })

        # DB updates immediately
        mc.is_deleted = False
        mc.category = None
        if mi:
            mi.is_in_sorter = True
    
    db.commit()

    key_id = b2_acc.key_id
    app_key = b2_acc.application_key
    target_bucket = b2_acc.bucket_name

    def perform_physical_restore(b2_key, b2_secret, items, target_bucket_name):
        client = B2Client(b2_key, b2_secret)
        # We need a new session in background thread
        local_db = SessionLocal()
        try:
            for item in items:
                file_name = item["file_name"]
                mi_id = item["mi_id"]
                current_bucket = item["current_bucket"]
                
                try:
                    # Move in B2
                    new_version = client.move_file(current_bucket, target_bucket_name, file_name)
                    try:
                        client.move_file(f"{current_bucket}-thumbs", f"{target_bucket_name}-thumbs", file_name)
                    except Exception as th_err:
                        pass
                    
                    # Update new ID in DB if it was an active MediaItem
                    if mi_id:
                        db_mi = local_db.query(MediaItem).filter(MediaItem.id == mi_id).first()
                        if db_mi:
                            db_mi.bucket_name = target_bucket_name
                            db_mi.id = new_version.id_
                            local_db.commit()
                except Exception as b2_err:
                    logger.error(f"Failed to restore {file_name}: {b2_err}")
        finally:
            local_db.close()

    background_tasks.add_task(perform_physical_restore, key_id, app_key, items_to_restore, target_bucket)
    return {"status": "ok", "message": f"{len(items_to_restore)} elem visszaállítása megkezdődött."}



