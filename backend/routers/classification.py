from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import B2Account, MediaItem, MediaClassification
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from ..utils.b2_client import B2Client
from sqlalchemy import delete, and_, or_

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ClassificationRequest(BaseModel):
    file_name: str
    action: str # család, utazás, állatok, delete

class BulkReverseRequest(BaseModel):
    folder_path: Optional[str] = None
    category_filter: Optional[str] = None

bulk_reverse_status: Dict[str, Any] = {
    "is_running": False,
    "total": 0,
    "current": 0,
    "message": ""
}

@router.get("/classify")
def classify_page(request: Request):
    return templates.TemplateResponse("classify.html", {"request": request})

@router.get("/api/classify/next")
def get_next_for_classification(exclude: List[str] = Query(None), db: Session = Depends(get_db)):
    """ Returns the next unclassified image from the source bucket, excluding specified files. """
    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            raise HTTPException(status_code=400, detail="Nincs aktív B2 fiók konfigurálva.")
        
        if not b2_account.source_bucket_name:
            raise HTTPException(status_code=400, detail="A 'forras' vödör neve nincs megadva a beállításoknál.")

        # Query for the next item
        query = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            MediaItem.bucket_name == b2_account.source_bucket_name
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(MediaClassification.category == None, MediaClassification.is_deleted == False)
            )
        )

        if exclude:
            query = query.filter(~MediaItem.file_name.in_(exclude))

        media_item = query.first()

        if not media_item:
            return {"done": True, "message": "Nincs több kép a várólistán (forras vödör üres vagy minden kész)."}

        # Generate Authorized URL
        try:
            client = B2Client(b2_account.key_id, b2_account.application_key)
            url = client.get_download_url(
                b2_account.source_bucket_name,
                media_item.file_name,
                b2_account.cloudflare_proxy_url
            )
        except Exception as b2_err:
            logger.error(f"B2 URL generation failed for {media_item.file_name}: {b2_err}")
            raise HTTPException(status_code=500, detail=f"B2 hiba: {str(b2_err)}")

        # Count ALL remaining items (unclassified) in this bucket
        total_remaining = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            MediaItem.bucket_name == b2_account.source_bucket_name
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(MediaClassification.category == None, MediaClassification.is_deleted == False)
            )
        ).count()

        return {
            "done": False,
            "url": url,
            "file_name": media_item.file_name,
            "total_remaining": total_remaining
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in get_next_for_classification")
        raise HTTPException(status_code=500, detail=f"Váratlan hiba: {str(e)}")

def b2_move_background_task(key_id: str, app_key: str, source_bucket: str, dest_bucket: str, file_name: str):
    try:
        from ..utils.b2_client import B2Client
        client = B2Client(key_id, app_key)
        client.move_file(source_bucket, dest_bucket, file_name)
        logger.info(f"Background B2 move successful: {file_name} -> {dest_bucket}")
    except Exception as e:
        logger.error(f"Background B2 move failed for {file_name}: {e}")

import threading

@router.post("/api/classify")
def classify_image(req: ClassificationRequest, db: Session = Depends(get_db)):
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")

    try:
        if req.action == "delete":
            if not b2_account.trash_bucket_name:
                raise HTTPException(status_code=400, detail="Lomtár vödör (torles-elott) nincs beállítva.")
            
            # 1. Start pure background thread for B2 move
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, 
                b2_account.application_key, 
                b2_account.source_bucket_name, 
                b2_account.trash_bucket_name, 
                req.file_name
            )).start()
            
            # 2. Update DB Immediately
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            
            classification.is_deleted = True
            classification.category = None
            
            # 3. Update MediaItem list instantly (move to trash in DB)
            db.query(MediaItem).filter(
                MediaItem.file_name == req.file_name, 
                MediaItem.bucket_name == b2_account.source_bucket_name
            ).update({"bucket_name": b2_account.trash_bucket_name})
            
        else:
            # Classification (család, utazás, etc)
            if not b2_account.bucket_name:
                raise HTTPException(status_code=400, detail="Cél vödör (kepek02) nincs beállítva.")
            
            # 1. Start pure background thread for B2 move
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, 
                b2_account.application_key, 
                b2_account.source_bucket_name, 
                b2_account.bucket_name, 
                req.file_name
            )).start()
            
            # 2. Update DB Immediately
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            
            classification.category = req.action
            classification.is_deleted = False
            
            # 3. Update MediaItem list instantly (move to main bucket in DB)
            db.query(MediaItem).filter(
                MediaItem.file_name == req.file_name, 
                MediaItem.bucket_name == b2_account.source_bucket_name
            ).update({"bucket_name": b2_account.bucket_name})
            

        db.commit()
        return {"status": "ok"}

    except Exception as e:
        logger.exception(f"Classification error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/classify/sync")
def trigger_source_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        return {"error": "No active account"}
    
    from ..worker import sync_b2_worker
    background_tasks.add_task(sync_b2_worker, b2_account.id, target_bucket=b2_account.source_bucket_name)
    return {"message": "Forrás szinkronizáció elindítva."}

def get_bulk_reverse_filenames(folder_path: Optional[str], category_filter: Optional[str], db: Session, source_bucket: str, target_bucket: str) -> set:
    """Helper to collect filenames to move back based on filters."""
    filenames = set()

    # 1. Filenames from MediaClassification (Level 2 Instant Visibility)
    q_mc = db.query(MediaClassification.file_name).filter(MediaClassification.is_deleted == False)
    if folder_path:
        q_mc = q_mc.filter(MediaClassification.file_name.startswith(folder_path))
    
    if category_filter == "all":
        pass # No category filter
    elif category_filter:
        q_mc = q_mc.filter(MediaClassification.category == category_filter)
    else:
        q_mc = q_mc.filter(MediaClassification.category == None)
    
    filenames.update([row[0] for row in q_mc.all()])

    # 2. Filenames from MediaItem (Target Bucket)
    # Ensure we only include items that actually match the category filter
    q_mi = db.query(MediaItem.file_name).outerjoin(
        MediaClassification, MediaItem.file_name == MediaClassification.file_name
    ).filter(MediaItem.bucket_name == target_bucket)

    if folder_path:
        q_mi = q_mi.filter(MediaItem.file_name.startswith(folder_path))

    if category_filter == "all":
        pass # Include everything in target bucket
    elif category_filter:
        q_mi = q_mi.filter(MediaClassification.category == category_filter)
    else:
        # Only include items in target bucket that have NO category (Uncategorized)
        q_mi = q_mi.filter(or_(
            MediaClassification.file_name == None, 
            MediaClassification.category == None
        ))
    
    filenames.update([row[0] for row in q_mi.all()])
    return filenames

def perform_bulk_reverse(folder_path: Optional[str], category_filter: Optional[str], db: Session):
    global bulk_reverse_status
    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account or not b2_account.bucket_name or not b2_account.source_bucket_name:
            bulk_reverse_status = {"is_running": False, "total": 0, "current": 0, "message": "Hiányzó B2 konfiguráció"}
            return
        
        # Use helper
        filenames = get_bulk_reverse_filenames(
            folder_path, category_filter, db, 
            b2_account.source_bucket_name, b2_account.bucket_name
        )

        items_to_move = sorted(list(filenames))
        total = len(items_to_move)

        bulk_reverse_status = {"is_running": True, "total": total, "current": 0, "message": f"{total} kép mozgatása folyamatban..."}
        
        if total == 0:
            bulk_reverse_status["is_running"] = False
            bulk_reverse_status["message"] = "Nincs mozgatható kép a kiválasztott feltételekkel."
            return

        client = B2Client(b2_account.key_id, b2_account.application_key)
        
        for i, file_name in enumerate(items_to_move):
            bulk_reverse_status["current"] = i + 1
            try:
                # Attempt to find MediaItem to get details, but fallback if missing
                item = db.query(MediaItem).filter(MediaItem.file_name == file_name).first()
                mime = item.mime_type if item else "image/jpeg"
                current_bucket = item.bucket_name if item else b2_account.bucket_name

                # 1. Move file in B2: from target bucket back to source
                new_version = client.move_file(current_bucket, b2_account.source_bucket_name, file_name)
                
                # 2. Delete old MediaItem records for this file (across all buckets to be safe)
                db.execute(delete(MediaItem).where(MediaItem.file_name == file_name))
                
                # 3. Add to source bucket index
                new_item = MediaItem(
                    id=new_version.id_,
                    b2_account_id=b2_account.id,
                    bucket_name=b2_account.source_bucket_name,
                    file_name=file_name,
                    mime_type=mime,
                )
                db.merge(new_item)
                
                # 4. Delete classification record
                db.execute(delete(MediaClassification).where(MediaClassification.file_name == file_name))
                db.commit()
            except Exception as e:
                logger.error(f"Error moving {file_name}: {e}")
                db.rollback()

        bulk_reverse_status["is_running"] = False
        bulk_reverse_status["message"] = f"Kész! {total} kép sikeresen visszamozgatva a forrás vödörbe."
        
    except Exception as e:
        logger.exception("Bulk reverse move error")
        bulk_reverse_status["is_running"] = False
        bulk_reverse_status["message"] = f"Hiba történt: {str(e)}"
    finally:
        db.close()

@router.post("/api/classification/bulk-reverse")
def start_bulk_reverse(req: BulkReverseRequest, background_tasks: BackgroundTasks):
    global bulk_reverse_status
    if bulk_reverse_status.get("is_running"):
        raise HTTPException(status_code=400, detail="Már fut egy visszamozgatás.")
    
    # Create an independent session for the background task
    db = SessionLocal()
    background_tasks.add_task(perform_bulk_reverse, req.folder_path, req.category_filter, db)
    return {"status": "started"}

@router.get("/api/classification/bulk-reverse/count")
def get_bulk_reverse_count(folder_path: Optional[str] = Query(None), category_filter: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Returns the number of items that would be moved back."""
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account or not b2_account.bucket_name or not b2_account.source_bucket_name:
         return {"count": 0}
    
    filenames = get_bulk_reverse_filenames(
        folder_path, category_filter, db, 
        b2_account.source_bucket_name, b2_account.bucket_name
    )
    return {"count": len(filenames)}

@router.get("/api/classification/bulk-reverse/status")
def get_bulk_reverse_status():
    global bulk_reverse_status
    return bulk_reverse_status
