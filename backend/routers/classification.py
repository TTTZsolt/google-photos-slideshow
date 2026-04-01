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

@router.post("/api/classify")
def classify_image(req: ClassificationRequest, db: Session = Depends(get_db)):
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")

    client = B2Client(b2_account.key_id, b2_account.application_key)

    try:
        if req.action == "delete":
            if not b2_account.trash_bucket_name:
                raise HTTPException(status_code=400, detail="Lomtár vödör (torles-elott) nincs beállítva.")
            
            # 1. Move in B2
            client.move_file(b2_account.source_bucket_name, b2_account.trash_bucket_name, req.file_name)
            
            # 2. Update DB
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            
            classification.is_deleted = True
            classification.category = None
            
            # Delete from MediaItem (so it doesn't show up in next calls)
            db.execute(delete(MediaItem).where(MediaItem.file_name == req.file_name, MediaItem.bucket_name == b2_account.source_bucket_name))
            
        else:
            # Classification (család, utazás, etc)
            if not b2_account.bucket_name:
                raise HTTPException(status_code=400, detail="Cél vödör (kepek02) nincs beállítva.")
            
            # 1. Move in B2 (Copy to kepek02, Delete from forras)
            new_version = client.move_file(b2_account.source_bucket_name, b2_account.bucket_name, req.file_name)
            
            # 2. Update/Create Classification
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            
            classification.category = req.action
            classification.is_deleted = False
            
            # 3. Update MediaItem record
            # Remove from forras
            db.execute(delete(MediaItem).where(MediaItem.file_name == req.file_name, MediaItem.bucket_name == b2_account.source_bucket_name))
            
            # Add to kepek02 (or Update)
            new_item = MediaItem(
                id=new_version.id_,
                b2_account_id=b2_account.id,
                bucket_name=b2_account.bucket_name,
                file_name=req.file_name,
                mime_type="image/jpeg", # TODO: detect properly or keep from before
                # size and creation_time could be copied from previous record but let's keep it simple
            )
            db.merge(new_item)

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

def perform_bulk_reverse(folder_path: Optional[str], category_filter: Optional[str], db: Session):
    global bulk_reverse_status
    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account or not b2_account.bucket_name or not b2_account.source_bucket_name:
            bulk_reverse_status = {"is_running": False, "total": 0, "current": 0, "message": "Hiányzó B2 konfiguráció"}
            return
        
        # Query media items in kepek02
        query = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(MediaItem.bucket_name == b2_account.bucket_name)

        if folder_path:
            if not folder_path.endswith('/'):
                folder_path += '/'
            query = query.filter(MediaItem.file_name.startswith(folder_path))
        
        if category_filter == "all":
            # No filtering by category, move everything in the folder
            pass
        elif category_filter:
            query = query.filter(MediaClassification.category == category_filter)
        else:
            # uncategorized: either no record or null category
            from sqlalchemy import or_
            query = query.filter(or_(
                MediaClassification.file_name == None,
                MediaClassification.category == None
            ))
            
        items = query.all()
        total = len(items)
        bulk_reverse_status = {"is_running": True, "total": total, "current": 0, "message": f"{total} kép mozgatása folyamatban..."}
        
        if total == 0:
            bulk_reverse_status["is_running"] = False
            bulk_reverse_status["message"] = "Nincs mozgatható kép a kiválasztott feltételekkel."
            return

        client = B2Client(b2_account.key_id, b2_account.application_key)
        
        for i, item in enumerate(items):
            bulk_reverse_status["current"] = i + 1
            file_name = item.file_name
            try:
                # 1. Move file in B2: from kepek02 to forras
                new_version = client.move_file(b2_account.bucket_name, b2_account.source_bucket_name, file_name)
                
                # 2. Delete MediaItem from kepek02
                db.execute(delete(MediaItem).where(MediaItem.file_name == file_name, MediaItem.bucket_name == b2_account.bucket_name))
                
                # Add to forras
                new_item = MediaItem(
                    id=new_version.id_,
                    b2_account_id=b2_account.id,
                    bucket_name=b2_account.source_bucket_name,
                    file_name=file_name,
                    mime_type=item.mime_type,
                )
                db.merge(new_item)
                
                # 3. Delete classification
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

@router.get("/api/classification/bulk-reverse/status")
def get_bulk_reverse_status():
    global bulk_reverse_status
    return bulk_reverse_status
