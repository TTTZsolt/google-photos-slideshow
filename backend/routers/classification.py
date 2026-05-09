from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import B2Account, MediaItem, MediaClassification, CategoryDefinition
from pydantic import BaseModel
from ..version import VERSION
from typing import Optional, Dict, Any, List
import logging
from ..utils.b2_client import B2Client
from sqlalchemy import delete, and_, or_
import concurrent.futures
import threading

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")
templates.env.globals.update(version=VERSION)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ClassificationRequest(BaseModel):
    file_name: str
    action: str # actual category name or "delete"

class CategoryCreate(BaseModel):
    name: str # internal name, lowercase
    display_name: str
    icon: str = "tag"
    color: str = "#6366f1"
    order: int = 0

class CategoryResponse(BaseModel):
    id: int
    name: str
    display_name: str
    icon: str
    color: str
    order: int

    class Config:
        from_attributes = True

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
    return templates.TemplateResponse("classify.html", {"request": request, "version": VERSION})

@router.get("/api/classify/next")
def get_next_for_classification(exclude: List[str] = Query(None), db: Session = Depends(get_db)):
    """ Returns the next image for classification. Looks in both source bucket and items marked with is_in_sorter. """
    try:
        logger.info("DEBUG: get_next_for_classification CALLED")
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            raise HTTPException(status_code=400, detail="Nincs aktív B2 fiók konfigurálva.")
        
        # ZERO-MOVE Logic: ONLY items explicitly marked for sorting
        query = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            MediaItem.is_in_sorter == True
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(MediaClassification.category == None, MediaClassification.is_deleted == False)
            )
        ).order_by(MediaItem.file_name.asc()) # Alphabetical/Folder order

        if exclude:
            query = query.filter(~MediaItem.file_name.in_(exclude))

        media_item = query.first()

        if not media_item:
            return {"done": True, "message": "Nincs több kép a várólistán."}

        # Generate Authorized URL
        try:
            client = B2Client(b2_account.key_id, b2_account.application_key)
            url = client.get_download_url(
                media_item.bucket_name,
                media_item.file_name,
                b2_account.cloudflare_proxy_url
            )
        except Exception as b2_err:
            logger.error(f"B2 URL generation failed for {media_item.file_name}: {b2_err}")
            raise HTTPException(status_code=500, detail=f"B2 hiba: {str(b2_err)}")

        # Count ALL remaining items for the UI
        total_remaining = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            MediaItem.is_in_sorter == True
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(MediaClassification.category == None, MediaClassification.is_deleted == False)
            )
        ).count()

        return {
            "done": False,
            "url": url,
            "thumb_url": client.get_download_url(f"{media_item.bucket_name}-thumbs", media_item.file_name, b2_account.cloudflare_proxy_url),
            "file_name": media_item.file_name,
            "total_remaining": total_remaining
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in get_next_for_classification")
        raise HTTPException(status_code=500, detail=f"Váratlan hiba: {str(e)}")

def b2_move_background_task(key_id: str, app_key: str, source_bucket: str, dest_bucket: str, file_name: str, file_info: dict = None):
    try:
        from ..utils.b2_client import B2Client
        client = B2Client(key_id, app_key)
        client.move_file(source_bucket, dest_bucket, file_name, file_info=file_info)
        logger.info(f"Background B2 move successful: {file_name} -> {dest_bucket} (meta: {file_info})")
    except Exception as e:
        logger.error(f"Background B2 move failed for {file_name}: {e}")

@router.post("/api/classify")
def classify_image(req: ClassificationRequest, db: Session = Depends(get_db)):
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")

    media_item = db.query(MediaItem).filter(MediaItem.file_name == req.file_name).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Kép nem található az adatbázisban.")

    try:
        source_bucket = media_item.bucket_name
        
        if req.action == "delete":
            target_bucket = b2_account.trash_bucket_name
            if not target_bucket:
                raise HTTPException(status_code=400, detail="Lomtár vödör nincs beállítva.")
            
            # Start background moves (Original + Thumb)
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, req.file_name
            )).start()
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", req.file_name
            )).start()
            
            # Update DB
            media_item.bucket_name = target_bucket
            media_item.is_in_sorter = False
            
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            classification.is_deleted = True
            classification.category = None
            
        else:
            # Classification (család, utazás, etc)
            target_bucket = b2_account.bucket_name
            file_info = {"category": req.action}
            
            if source_bucket != target_bucket:
                # Need to move physically
                threading.Thread(target=b2_move_background_task, args=(
                    b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, req.file_name, file_info
                )).start()
                threading.Thread(target=b2_move_background_task, args=(
                    b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", req.file_name, file_info
                )).start()
                media_item.bucket_name = target_bucket
            else:
                # Already in target bucket! Just update metadata in background
                def update_metadata_task(key_id, app_key, bucket, file_name, info):
                    try:
                        client = B2Client(key_id, app_key)
                        client.update_file_info(bucket, file_name, info)
                    except Exception as e:
                        logger.error(f"Metadata update failed for {file_name}: {e}")

                threading.Thread(target=update_metadata_task, args=(
                    b2_account.key_id, b2_account.application_key, target_bucket, req.file_name, file_info
                )).start()

            # Update DB
            media_item.is_in_sorter = False
            classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
            if not classification:
                classification = MediaClassification(file_name=req.file_name)
                db.add(classification)
            classification.category = req.action
            classification.is_deleted = False

        db.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.exception(f"Classification error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/classify/undo")
def undo_classification(req: ClassificationRequest, db: Session = Depends(get_db)):
    """ Reverts the last classification in the UI. Sets is_in_sorter=True and clears category. """
    try:
        media_item = db.query(MediaItem).filter(MediaItem.file_name == req.file_name).first()
        if not media_item:
             raise HTTPException(status_code=404, detail="Kép nem található.")

        # Revert DB state
        media_item.is_in_sorter = True
        
        classification = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
        if classification:
            classification.category = None
            classification.is_deleted = False

        db.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.exception(f"Undo error: {e}")
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
    """ ZERO-MOVE Mover: Just marks items in DB for re-classification. """
    global bulk_reverse_status
    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            bulk_reverse_status = {"is_running": False, "total": 0, "current": 0, "message": "Nincs aktív B2 fiók"}
            return
        
        # Use existing helper to get filenames matching criteria
        filenames = get_bulk_reverse_filenames(
            folder_path, category_filter, db, 
            b2_account.source_bucket_name, b2_account.bucket_name
        )

        items_to_mark = sorted(list(filenames))
        total = len(items_to_mark)

        bulk_reverse_status = {"is_running": True, "total": total, "current": 0, "message": f"{total} kép előkészítése..."}
        
        if total == 0:
            bulk_reverse_status["is_running"] = False
            bulk_reverse_status["message"] = "Nincs ilyen kép a kiválasztott feltételekkel."
            return

        # Parallelize DB updates
        batch_size = 100
        for i in range(0, total, batch_size):
            batch = items_to_mark[i:i+batch_size]
            bulk_reverse_status["current"] = i + len(batch)
            
            # 1. Clear classification
            db.execute(delete(MediaClassification).where(MediaClassification.file_name.in_(batch)))
            
            # 2. Mark as in sorter
            db.query(MediaItem).filter(MediaItem.file_name.in_(batch)).update({"is_in_sorter": True}, synchronize_session=False)
            
            db.commit()

        bulk_reverse_status["is_running"] = False
        bulk_reverse_status["message"] = f"Kész! {total} kép azonnal válogatható a Szortírozóban."
        
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

# --- Category Management ---

@router.get("/api/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(CategoryDefinition).order_by(CategoryDefinition.order.asc()).all()

@router.post("/api/categories", response_model=CategoryResponse)
def create_category(cat: CategoryCreate, db: Session = Depends(get_db)):
    # Check if already exists
    existing = db.query(CategoryDefinition).filter(CategoryDefinition.name == cat.name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ez a kategória már létezik.")
    
    new_cat = CategoryDefinition(
        name=cat.name.lower(),
        display_name=cat.display_name,
        icon=cat.icon,
        color=cat.color,
        order=cat.order
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(CategoryDefinition).filter(CategoryDefinition.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategória nem található.")
    
    db.delete(cat)
    db.commit()
    return {"status": "ok"}
@router.post("/api/classification/sorter/reset")
def reset_sorter(db: Session = Depends(get_db)):
    """ Resets the is_in_sorter flag for all items. """
    try:
        count = db.query(MediaItem).filter(MediaItem.is_in_sorter == True).update({"is_in_sorter": False})
        db.commit()
        return {"message": f"Szortírozó alaphelyzetbe állítva. {count} elem eltávolítva."}
    except Exception as e:
        db.rollback()
        logger.error(f"Sorter reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
