from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import B2Account, MediaItem, MediaClassification, CategoryDefinition, DeletedContentHash
from pydantic import BaseModel
from ..version import VERSION
from typing import Optional, Dict, Any, List
import logging
from ..utils.b2_client import B2Client
from sqlalchemy import delete, and_, or_
import concurrent.futures
import threading
import os
import requests
from io import BytesIO
from PIL import Image

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

class BulkManualItem(BaseModel):
    file_name: str
    category: str # "delete", "uncategorized", or actual category name

class BulkManualRequest(BaseModel):
    items: List[BulkManualItem]

class RotateImageRequest(BaseModel):
    file_name: str
    direction: str # "left" or "right"

class CategoryCreate(BaseModel):
    name: str # internal name, lowercase
    display_name: str
    icon: str = "tag"
    color: str = "#6366f1"
    order: int = 0
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    display_name: str
    icon: str = "tag"
    color: str = "#6366f1"
    order: Optional[int] = 0
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    display_name: str
    icon: str
    color: str
    order: int
    description: Optional[str] = None

    class Config:
        from_attributes = True

class BulkReverseRequest(BaseModel):
    folder_path: Optional[str] = None
    category_filter: Optional[str] = None
    ai_mode: Optional[str] = "manual" # "manual", "ai-delete-only", "ai-full"
    ai_model: Optional[str] = "gemini-2.5-flash"
    ai_custom_rules: Optional[str] = ""

bulk_reverse_status: Dict[str, Any] = {
    "is_running": False,
    "total": 0,
    "current": 0,
    "message": ""
}

CUSTOM_RULES_FILE = "egyeni_torlesi_szempontok.txt"

class CustomRulesRequest(BaseModel):
    text: str

@router.get("/api/classification/custom-rules")
def get_custom_rules():
    """ Returns the externally-editable custom AI deletion rules file content. """
    if os.path.exists(CUSTOM_RULES_FILE):
        with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
            return {"text": f.read()}
    return {"text": ""}

@router.post("/api/classification/custom-rules")
def save_custom_rules(req: CustomRulesRequest):
    """ Persists the custom AI deletion rules to a plain text file (clearing it if text is empty). """
    with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
        f.write(req.text)
    return {"status": "ok"}

@router.get("/api/media/check-sha1/{sha1}")
def check_sha1(sha1: str, db: Session = Depends(get_db)):
    """Checks a content SHA1 before an external upload (e.g. the Android auto-
    feltoltes script) - same purpose as the Takeout uploader's SHA1 check:
    avoid re-uploading a file that's already in the main bucket, and never
    resurrect a file that was intentionally deleted (tombstoned)."""
    b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
    exists = False
    if b2_acc:
        exists = db.query(MediaItem).filter(
            MediaItem.bucket_name == b2_acc.bucket_name,
            MediaItem.sha1 == sha1
        ).first() is not None
    deleted = db.query(DeletedContentHash).filter(DeletedContentHash.sha1 == sha1).first() is not None
    return {"exists": exists, "deleted": deleted}

@router.get("/classify")
def classify_page(request: Request):
    return templates.TemplateResponse("classify.html", {"request": request, "version": VERSION})

@router.get("/folder-kanban")
def folder_kanban_page(request: Request):
    return templates.TemplateResponse("folder_kanban.html", {"request": request, "version": VERSION})

@router.get("/api/folders/items")
def get_folder_items(folder_path: str = Query(""), limit: int = Query(100), offset: int = Query(0), db: Session = Depends(get_db)):
    """Returns up to `limit` items (recursively) under folder_path, starting at `offset`,
    with download/thumb URLs and their current category - a data feed for the Folder Kanban view."""
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")

    prefix = folder_path
    if prefix and not prefix.endswith('/'):
        prefix += '/'

    # Include the trash bucket too, so images marked "delete" in the Kanban
    # (which are moved there immediately) still show up in the Törlendő column
    # until they're permanently removed via the Trash page.
    bucket_names = [b2_account.bucket_name]
    if b2_account.trash_bucket_name:
        bucket_names.append(b2_account.trash_bucket_name)

    query = db.query(MediaItem).filter(MediaItem.bucket_name.in_(bucket_names))
    if prefix:
        query = query.filter(MediaItem.file_name.like(f"{prefix}%"))
    query = query.order_by(MediaItem.file_name.asc())

    total_count = query.count()
    media_items = query.offset(offset).limit(limit).all()

    file_names = [mi.file_name for mi in media_items]
    classifications = {}
    if file_names:
        rows = db.query(MediaClassification.file_name, MediaClassification.category, MediaClassification.is_deleted).filter(
            MediaClassification.file_name.in_(file_names)
        ).all()
        classifications = {fn: ('delete' if is_deleted else cat) for fn, cat, is_deleted in rows}

    client = B2Client(b2_account.key_id, b2_account.application_key)
    items = []
    for mi in media_items:
        items.append({
            "file_name": mi.file_name,
            "category": classifications.get(mi.file_name),
            "url": client.get_download_url(mi.bucket_name, mi.file_name, b2_account.cloudflare_proxy_url),
            "thumb_url": client.get_download_url(f"{mi.bucket_name}-thumbs", mi.file_name, b2_account.cloudflare_proxy_url),
        })

    return {"items": items, "has_more": (offset + limit) < total_count}

@router.post("/api/classification/rotate-image")
def rotate_image(req: RotateImageRequest, db: Session = Depends(get_db)):
    """Rotates an image (and its thumbnail) 90 degrees left or right, in place, on B2."""
    if req.direction not in ("left", "right"):
        raise HTTPException(status_code=400, detail="direction must be 'left' or 'right'")

    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")

    mi = db.query(MediaItem).filter(MediaItem.file_name == req.file_name).first()
    if not mi:
        raise HTTPException(status_code=404, detail="Fájl nem található.")

    transpose = Image.Transpose.ROTATE_90 if req.direction == "left" else Image.Transpose.ROTATE_270

    client = B2Client(b2_account.key_id, b2_account.application_key)

    def rotate_and_reupload(bucket_name: str, file_name: str):
        # Bypass the Cloudflare proxy for both the download (must be the true
        # latest bytes, not a stale cached copy) and the returned URL (must
        # reflect the just-uploaded rotation immediately, not the proxy's cache).
        url = client.get_download_url(bucket_name, file_name, b2_account.cloudflare_proxy_url, use_proxy=False)
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        rotated = img.transpose(transpose)
        buf = BytesIO()
        rotated.convert("RGB").save(buf, format="JPEG", quality=92)
        client.upload_byte_stream(bucket_name, file_name, buf.getvalue(), content_type="image/jpeg")
        return client.get_download_url(bucket_name, file_name, b2_account.cloudflare_proxy_url, use_proxy=False)

    try:
        fresh_url = rotate_and_reupload(mi.bucket_name, mi.file_name)
        fresh_thumb_url = rotate_and_reupload(f"{mi.bucket_name}-thumbs", mi.file_name)
    except Exception as e:
        logger.error(f"Rotate failed for {req.file_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Forgatás sikertelen: {e}")

    return {"success": True, "url": fresh_url, "thumb_url": fresh_thumb_url}

@router.get("/api/classify/next")
def get_next_for_classification(exclude: List[str] = Query(None), db: Session = Depends(get_db)):
    """ Returns the next image for classification. Looks in both source bucket and items marked with is_in_sorter. """
    try:
        logger.info("DEBUG: get_next_for_classification CALLED")
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            raise HTTPException(status_code=400, detail="Nincs aktív B2 fiók konfigurálva.")
        
        # ZERO-MOVE Logic: ONLY items explicitly marked for sorting, excluding those with pending AI suggestions
        query = db.query(MediaItem).outerjoin(
            MediaClassification, MediaItem.file_name == MediaClassification.file_name
        ).filter(
            MediaItem.is_in_sorter == True
        ).filter(
            or_(
                MediaClassification.file_name == None,
                and_(
                    MediaClassification.category == None, 
                    MediaClassification.is_deleted == False,
                    or_(MediaClassification.ai_status == None, MediaClassification.ai_status != "pending")
                )
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
    # Exclude items that are currently pending AI classification
    q_mc = db.query(MediaClassification.file_name).filter(
        MediaClassification.is_deleted == False,
        or_(MediaClassification.ai_status == None, MediaClassification.ai_status != "pending")
    )
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
    # Ensure we only include items that match the filter and are not pending AI classification
    q_mi = db.query(MediaItem.file_name).outerjoin(
        MediaClassification, MediaItem.file_name == MediaClassification.file_name
    ).filter(
        MediaItem.bucket_name == target_bucket,
        or_(MediaClassification.file_name == None, or_(MediaClassification.ai_status == None, MediaClassification.ai_status != "pending"))
    )

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

def process_ai_classification(filenames: List[str], ai_mode: str, ai_model: str, custom_rules: str, db: Session):
    global bulk_reverse_status
    try:
        import time
        from datetime import datetime, timedelta
        from ..utils.ai_service import analyze_image_for_sorting, pick_best_from_duplicate_group
        from ..utils.duplicate_detection import compute_dhash, group_near_duplicates
        from ..utils.b2_client import B2Client
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            bulk_reverse_status["is_running"] = False
            return
        client = B2Client(b2_account.key_id, b2_account.application_key)

        categories = db.query(CategoryDefinition).all()
        # Separate normal categories and system delete rules
        delete_rules = ""
        cat_details = {}
        for c in categories:
            if c.name == "delete":
                delete_rules = c.description or ""
            else:
                cat_details[c.name] = c.description or ""

        # Combine system delete rules with custom rules from request
        combined_rules = delete_rules
        if custom_rules:
            combined_rules = f"{delete_rules}\n{custom_rules}".strip()

        total_imgs = len(filenames)

        # Rate-limiting: images are processed concurrently (GEMINI_MAX_CONCURRENCY workers,
        # default 1 = old sequential behavior), but every worker shares this single pacer so
        # calls are never started more often in aggregate than the configured RPM allows.
        # Free-tier Gemini defaults to 12 RPM. A paid/billed API key supports a much higher
        # RPM - set GEMINI_RPM_LIMIT env var to raise it (e.g. GEMINI_RPM_LIMIT=900).
        rpm_limit = int(os.environ.get("GEMINI_RPM_LIMIT", "12"))
        min_interval = (60.0 / rpm_limit) if rpm_limit > 0 else 0.0
        max_concurrency = max(1, int(os.environ.get("GEMINI_MAX_CONCURRENCY", "1")))
        rate_lock = threading.Lock()
        next_call_time = [0.0]
        progress_lock = threading.Lock()

        def wait_for_rate_slot():
            if min_interval <= 0:
                return
            with rate_lock:
                now = time.monotonic()
                wait = next_call_time[0] - now
                if wait > 0:
                    time.sleep(wait)
                    now = time.monotonic()
                next_call_time[0] = now + min_interval

        # --- Duplikatum-eloszures --------------------------------------------------
        # A hagyomanyos, kepenkent kulon-kulon hivott AI-osztalyozas soha nem latja
        # egyszerre ket kepet, igy nem tudja eldonteni, hogy egymas duplikatumai -
        # ezert nem tudta eddig ervenyesiteni az "ha tobb nagyon hasonlo kep van,
        # csak egyet tarts meg" egyeni szabalyt. Ez a lepes eloszor perceptual-hash
        # (dHash) alapjan, olcson csoportositja az egymas utan kovetkezo, vizualisan
        # szinte azonos kepeket (pl. sorozatfelvetelek), majd csoportonkent EGYETLEN
        # tobb-kepes AI-hivassal eldonteti, melyiket erdemes megtartani. A vesztesek
        # azonnal torlesre-javasoltkent kerulnek jelolesre, es kimaradnak a lenti
        # egyedi-kepes AI-korbol (ami felulirna ezt a dontest).
        duplicate_losers = set()
        duplicate_losers_lock = threading.Lock()
        try:
            bulk_reverse_status["message"] = "Duplikátumok keresése (kép-hasonlóság elemzése)..."
            sorted_filenames = sorted(filenames)
            hash_threshold = int(os.environ.get("DUPLICATE_HASH_THRESHOLD", "10"))

            item_lookup = {
                mi.file_name: mi
                for mi in db.query(MediaItem).filter(MediaItem.file_name.in_(sorted_filenames)).all()
            }

            def compute_hash_for(fname):
                mi = item_lookup.get(fname)
                if not mi:
                    return fname, None
                try:
                    thumb_url = client.get_download_url(f"{mi.bucket_name}-thumbs", fname, b2_account.cloudflare_proxy_url)
                    resp = requests.get(thumb_url, timeout=15)
                    resp.raise_for_status()
                    return fname, compute_dhash(resp.content)
                except Exception as hash_err:
                    logger.warning(f"Duplikátum-hash számítás sikertelen ehhez: {fname}: {hash_err}")
                    return fname, None

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as hash_executor:
                hash_results = list(hash_executor.map(compute_hash_for, sorted_filenames))

            valid_hashes = [(fname, h) for fname, h in hash_results if h is not None]
            duplicate_groups = [g for g in group_near_duplicates(valid_hashes, threshold=hash_threshold) if len(g) > 1]

            if duplicate_groups:
                bulk_reverse_status["message"] = (
                    f"{len(duplicate_groups)} duplikátum-csoport azonosítva, legjobb példány kiválasztása..."
                )

            def resolve_group(group):
                try:
                    urls = [
                        client.get_download_url(f"{item_lookup[fname].bucket_name}-thumbs", fname, b2_account.cloudflare_proxy_url)
                        for fname in group
                    ]

                    wait_for_rate_slot()
                    keep_idx, used_model = pick_best_from_duplicate_group(urls, combined_rules, ai_model)
                    if used_model != ai_model:
                        bulk_reverse_status["fallback_model_used"] = used_model

                    group_db = SessionLocal()
                    try:
                        for i, fname in enumerate(group):
                            if i == keep_idx:
                                continue
                            with duplicate_losers_lock:
                                duplicate_losers.add(fname)
                            mc = group_db.query(MediaClassification).filter(MediaClassification.file_name == fname).first()
                            if not mc:
                                mc = MediaClassification(file_name=fname)
                                group_db.add(mc)
                            mc.ai_suggested_category = "delete"
                            mc.ai_status = "pending"
                            mc.ai_error = None
                        group_db.commit()
                    finally:
                        group_db.close()
                except Exception as group_err:
                    logger.warning(f"Duplikátum-csoport AI döntés sikertelen ({group}): {group_err}")
                finally:
                    with progress_lock:
                        bulk_reverse_status["current"] = bulk_reverse_status.get("current", 0) + (len(group) - 1)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as group_executor:
                group_futures = [group_executor.submit(resolve_group, g) for g in duplicate_groups]
                for gf in concurrent.futures.as_completed(group_futures):
                    gf.result()
        except Exception as dup_err:
            logger.error(f"Duplikátum-előszűrési lépés hiba: {dup_err}")

        # A duplikatum-vesztesek mar el vannak donteve (torlesre javasolva) - ne
        # menjenek at meg egyszer az egyedi-kepes AI-osztalyozason is.
        filenames = [f for f in filenames if f not in duplicate_losers]

        def classify_one(fname):
            if not bulk_reverse_status.get("is_running", False):
                return
            # Each concurrent worker needs its own DB session - SQLAlchemy sessions
            # are not thread-safe to share (same pattern as the B2 background threads).
            item_db = SessionLocal()
            try:
                mi = item_db.query(MediaItem).filter(MediaItem.file_name == fname, MediaItem.is_in_sorter == True).first()
                if not mi:
                    return

                # Quota retry loop
                retry_count = 0
                while True:
                    wait_for_rate_slot()
                    try:
                        thumb_url = client.get_download_url(f"{mi.bucket_name}-thumbs", fname, b2_account.cloudflare_proxy_url)
                        suggested, used_model = analyze_image_for_sorting(thumb_url, cat_details, combined_rules, ai_model)

                        # If a fallback happened (the used model is different than requested), note it in status
                        if used_model != ai_model:
                            bulk_reverse_status["fallback_model_used"] = used_model

                        if ai_mode == "ai-delete-only" and suggested != "delete":
                            suggested = None

                        mc = item_db.query(MediaClassification).filter(MediaClassification.file_name == fname).first()
                        if not mc:
                            mc = MediaClassification(file_name=fname)
                            item_db.add(mc)

                        if suggested:
                            mc.ai_suggested_category = suggested
                            mc.ai_status = "pending"
                            mc.ai_error = None
                        else:
                            mc.ai_status = None
                            mc.ai_error = None

                        item_db.commit()
                        break # Success, proceed to next image
                    except Exception as item_err:
                        err_msg = str(item_err).lower()
                        is_quota = "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "rate limit" in err_msg

                        if is_quota:
                            if retry_count == 0:
                                retry_count += 1
                                logger.warning(f"AI Quota limit hit for {fname}. Sleeping 2 minutes for retry...")
                                bulk_reverse_status["message"] = "Percen belüli AI limit elérve. Várok 2 percet az újraindításig..."
                                time.sleep(120)
                                continue # Retry same image
                            else:
                                logger.error(f"AI Daily Quota limit hit for {fname}. Pausing classification until tomorrow.")

                                now = datetime.now()
                                tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
                                tomorrow_8am = tomorrow.replace(hour=8, minute=0, second=0)
                                sleep_seconds = int((tomorrow_8am - now).total_seconds())

                                if sleep_seconds < 3600:
                                    sleep_seconds = 3600
                                elif sleep_seconds > 86400:
                                    sleep_seconds = 86400

                                bulk_reverse_status["message"] = f"A napi AI limit elfogyott. Az elemzés szünetel holnap reggelig (várakozás: {sleep_seconds // 3600} óra)..."
                                time.sleep(sleep_seconds)
                                retry_count = 0
                                continue # Retry same image after tomorrow's sleep
                        else:
                            # Non-quota error, save failure and continue
                            logger.error(f"Failed AI classification for {fname}: {item_err}")
                            mc = item_db.query(MediaClassification).filter(MediaClassification.file_name == fname).first()
                            if not mc:
                                mc = MediaClassification(file_name=fname)
                                item_db.add(mc)
                            mc.ai_status = "failed"
                            mc.ai_error = str(item_err)
                            item_db.commit()
                            break # Stop retrying, proceed to next image
            finally:
                item_db.close()

            with progress_lock:
                bulk_reverse_status["current"] = bulk_reverse_status.get("current", 0) + 1
                bulk_reverse_status["message"] = f"AI elemzés folyamatban: {bulk_reverse_status['current']}/{total_imgs} kép..."

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            futures = [executor.submit(classify_one, fname) for fname in filenames]
            for future in concurrent.futures.as_completed(futures):
                future.result()  # re-raise unexpected worker exceptions here

        bulk_reverse_status["message"] = f"Kész! {total_imgs} kép sikeresen szortírozva az AI által."
    except Exception as e:
        logger.error(f"AI Classification background task failed: {e}")
        bulk_reverse_status["message"] = f"AI elemzés hiba: {str(e)}"
    finally:
        bulk_reverse_status["is_running"] = False
        db.close()

def perform_bulk_reverse(folder_path: Optional[str], category_filter: Optional[str], ai_mode: str, ai_model: str, ai_custom_rules: str, db: Session):
    """ ZERO-MOVE Mover: Just marks items in DB for re-classification. Starts AI if requested. """
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
            
            # Mark as in sorter and clear AI statuses
            for item in batch:
                mc = db.query(MediaClassification).filter(MediaClassification.file_name == item).first()
                if not mc:
                    mc = MediaClassification(file_name=item)
                    db.add(mc)
                mc.category = None
                mc.ai_suggested_category = None
                mc.ai_status = None
                mc.ai_error = None
                
            db.query(MediaItem).filter(MediaItem.file_name.in_(batch)).update({"is_in_sorter": True}, synchronize_session=False)
            db.commit()

        # Clean up any residual 'failed' status entries to avoid stale warnings
        db.query(MediaClassification).filter(MediaClassification.ai_status == "failed").update({
            "ai_status": None,
            "ai_error": None
        })
        db.commit()

        if ai_mode != "manual":
            bulk_reverse_status["message"] = f"Kész! {total} kép hozzáadva. AI elemzés a háttérben indítva..."
            # Launch AI thread
            ai_db = SessionLocal()
            threading.Thread(target=process_ai_classification, args=(items_to_mark, ai_mode, ai_model, ai_custom_rules, ai_db)).start()
        else:
            bulk_reverse_status["message"] = f"Kész! {total} kép azonnal válogatható a Szortírozóban."
            bulk_reverse_status["is_running"] = False
        
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
    
    db = SessionLocal()
    background_tasks.add_task(perform_bulk_reverse, req.folder_path, req.category_filter, req.ai_mode, req.ai_model, req.ai_custom_rules, db)
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
    
    # Count pending AI items
    q_pending = db.query(MediaClassification.file_name).join(
        MediaItem, MediaClassification.file_name == MediaItem.file_name
    ).filter(
        MediaClassification.ai_status == "pending",
        MediaItem.is_in_sorter == True
    )
    if folder_path:
        q_pending = q_pending.filter(MediaClassification.file_name.startswith(folder_path))
        
    if category_filter == "all":
        pass
    elif category_filter:
        q_pending = q_pending.filter(MediaClassification.category == category_filter)
    else:
        q_pending = q_pending.filter(MediaClassification.category == None)
        
    return {
        "count": len(filenames),
        "pending_ai_count": q_pending.count()
    }

@router.get("/api/classification/bulk-reverse/status")
def get_bulk_reverse_status(db: Session = Depends(get_db)):
    """Returns the status of the background bulk reverse process."""
    global bulk_reverse_status
    status_copy = bulk_reverse_status.copy()
    
    # Calculate actual pending (successful AI suggestions awaiting review)
    pending_count = db.query(MediaClassification).join(
        MediaItem, MediaClassification.file_name == MediaItem.file_name
    ).filter(
        MediaClassification.ai_status == "pending",
        MediaItem.is_in_sorter == True
    ).count()
    
    # Calculate failed items in database
    failed_count = db.query(MediaClassification).filter(MediaClassification.ai_status == "failed").count()
    
    status_copy["pending_count"] = pending_count
    status_copy["failed_count"] = failed_count
    
    if failed_count > 0:
        example_err = db.query(MediaClassification.ai_error).filter(MediaClassification.ai_status == "failed").first()
        if example_err:
            status_copy["example_error"] = example_err[0]
            
    return status_copy

@router.post("/api/classification/bulk-reverse/stop")
def stop_bulk_reverse():
    """Stops the running background AI classification process."""
    global bulk_reverse_status
    if bulk_reverse_status.get("is_running"):
        bulk_reverse_status["is_running"] = False
        bulk_reverse_status["message"] = "Folyamat leállítva a felhasználó által."
        return {"status": "ok", "message": "Leállítás sikeres."}
    return {"status": "ignored", "message": "Nincs futó folyamat."}

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
        order=cat.order,
        description=cat.description
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.put("/api/categories/{cat_id}", response_model=CategoryResponse)
def update_category(cat_id: int, cat: CategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(CategoryDefinition).filter(CategoryDefinition.id == cat_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Kategória nem található.")
    
    db_cat.display_name = cat.display_name
    db_cat.icon = cat.icon
    db_cat.color = cat.color
    if cat.order is not None:
        db_cat.order = cat.order
    db_cat.description = cat.description
    
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(CategoryDefinition).filter(CategoryDefinition.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategória nem található.")
    if cat.name == "delete":
        raise HTTPException(status_code=400, detail="A rendszer szintű 'Törlés' kategória nem törölhető.")
    
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

class ApproveItemRequest(BaseModel):
    file_name: str
    action: str # "approve", "delete", "change_category"
    category: Optional[str] = None

@router.get("/api/classification/review-items")
def get_review_items(db: Session = Depends(get_db)):
    """ Returns a list of items analyzed by AI that are pending approval. """
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        return []
        
    client = B2Client(b2_account.key_id, b2_account.application_key)
    
    results = db.query(MediaClassification, MediaItem).join(
        MediaItem, MediaClassification.file_name == MediaItem.file_name
    ).filter(MediaClassification.ai_status == "pending", MediaItem.is_in_sorter == True).all()
    
    items = []
    for mc, mi in results:
        try:
            url = client.get_download_url(mi.bucket_name, mi.file_name, b2_account.cloudflare_proxy_url)
            thumb_url = client.get_download_url(f"{mi.bucket_name}-thumbs", mi.file_name, b2_account.cloudflare_proxy_url)
            
            items.append({
                "file_name": mc.file_name,
                "ai_suggested_category": mc.ai_suggested_category,
                "url": url,
                "thumb_url": thumb_url
            })
        except Exception as e:
            logger.warning(f"Could not generate URLs for review item {mc.file_name}: {e}")
            
    return items

class UpdateSuggestionRequest(BaseModel):
    file_name: str
    category: str

@router.post("/api/classification/update-suggestion")
def update_suggestion(req: UpdateSuggestionRequest, db: Session = Depends(get_db)):
    """ Updates the AI suggestion without finalizing it. """
    mc = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
    if not mc:
        raise HTTPException(status_code=404, detail="Kép nem található.")
    
    mc.ai_suggested_category = req.category
    db.commit()
    return {"status": "ok"}

@router.post("/api/classification/approve-item")
def approve_item(req: ApproveItemRequest, db: Session = Depends(get_db)):
    """ Approves, overrides or deletes a single AI suggestion. """
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")
        
    mc = db.query(MediaClassification).filter(MediaClassification.file_name == req.file_name).first()
    mi = db.query(MediaItem).filter(MediaItem.file_name == req.file_name).first()
    
    if not mc or not mi:
        raise HTTPException(status_code=404, detail="Kép nem található.")
        
    source_bucket = mi.bucket_name
    
    target_action = None
    if req.action == "approve":
        target_action = mc.ai_suggested_category
    elif req.action == "delete":
        target_action = "delete"
    elif req.action == "change_category":
        target_action = req.category
        
    if not target_action:
        raise HTTPException(status_code=400, detail="Nem meghatározható célművelet.")
        
    try:
        if target_action == "delete":
            target_bucket = b2_account.trash_bucket_name
            if not target_bucket:
                 raise HTTPException(status_code=400, detail="Lomtár vödör nincs beállítva.")
                 
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, req.file_name
            )).start()
            threading.Thread(target=b2_move_background_task, args=(
                b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", req.file_name
            )).start()
            
            mi.bucket_name = target_bucket
            mi.is_in_sorter = False
            mc.is_deleted = True
            mc.category = None
        else:
            target_bucket = b2_account.bucket_name
            if target_action == "uncategorized":
                mc.category = None
                mc.is_deleted = False
                mi.is_in_sorter = False
            else:
                file_info = {"category": target_action}
                if source_bucket != target_bucket:
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, req.file_name, file_info
                    )).start()
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", req.file_name, file_info
                    )).start()
                    mi.bucket_name = target_bucket
                else:
                    def update_metadata_task(key_id, app_key, bucket, file_name, info):
                        try:
                            client = B2Client(key_id, app_key)
                            client.update_file_info(bucket, file_name, info)
                        except Exception as e:
                            logger.error(f"Metadata update failed for {file_name}: {e}")

                    threading.Thread(target=update_metadata_task, args=(
                        b2_account.key_id, b2_account.application_key, target_bucket, req.file_name, file_info
                    )).start()
                    
                mc.category = target_action
                mc.is_deleted = False
                mi.is_in_sorter = False
                
        mc.ai_status = "approved"
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        db.rollback()
        logger.exception("Approve single item error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/classification/bulk-classify-manual")
def bulk_classify_manual(req: BulkManualRequest, db: Session = Depends(get_db)):
    """ Bulk classification for Folder Kanban. """
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")
        
    count = 0
    try:
        for item in req.items:
            target_action = item.category
            
            mi = db.query(MediaItem).filter(MediaItem.file_name == item.file_name).first()
            if not mi:
                continue
                
            source_bucket = mi.bucket_name
            mc = db.query(MediaClassification).filter(MediaClassification.file_name == item.file_name).first()
            if not mc:
                mc = MediaClassification(file_name=item.file_name)
                db.add(mc)
                
            # If target_action == "uncategorized", user put it back to Uncategorized.
            # In manual sorter, this means it's not categorized, so it shouldn't move.
            if target_action == "uncategorized":
                mc.category = None
                mc.is_deleted = False
                mi.is_in_sorter = False # It's not in the regular sorter queue anymore, it was manually viewed.
                # If it was previously moved to trash, move it back out so the bucket
                # matches the now-restored (non-deleted) state.
                if b2_account.trash_bucket_name and source_bucket == b2_account.trash_bucket_name:
                    target_bucket = b2_account.bucket_name
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, item.file_name
                    )).start()
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", item.file_name
                    )).start()
                    mi.bucket_name = target_bucket
                continue

            if target_action == "delete":
                target_bucket = b2_account.trash_bucket_name
                if not target_bucket:
                    continue
                threading.Thread(target=b2_move_background_task, args=(
                    b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, item.file_name
                )).start()
                threading.Thread(target=b2_move_background_task, args=(
                    b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", item.file_name
                )).start()
                mi.bucket_name = target_bucket
                mi.is_in_sorter = False
                mc.is_deleted = True
                mc.category = None
                count += 1
            else:
                target_bucket = b2_account.bucket_name
                file_info = {"category": target_action}
                
                if source_bucket != target_bucket:
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, item.file_name, file_info
                    )).start()
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", item.file_name, file_info
                    )).start()
                    mi.bucket_name = target_bucket
                else:
                    def update_metadata_task(key_id, app_key, bucket, file_name, info):
                        try:
                            client = B2Client(key_id, app_key)
                            client.update_file_info(bucket, file_name, info)
                        except Exception as e:
                            logger.error(f"Metadata update failed for {file_name}: {e}")

                    threading.Thread(target=update_metadata_task, args=(
                        b2_account.key_id, b2_account.application_key, target_bucket, item.file_name, file_info
                    )).start()
                    
                mi.is_in_sorter = False
                mc.category = target_action
                mc.is_deleted = False
                count += 1
                
        db.commit()
        return {"status": "ok", "count": count}
    except Exception as e:
        db.rollback()
        logger.exception("Bulk classify manual error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/classification/approve-all")
def approve_all_suggestions(db: Session = Depends(get_db)):
    """ Approves all pending AI suggestions at once. """
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="Nincs aktív B2 fiók.")
        
    results = db.query(MediaClassification, MediaItem).join(
        MediaItem, MediaClassification.file_name == MediaItem.file_name
    ).filter(MediaClassification.ai_status == "pending", MediaItem.is_in_sorter == True).all()
    
    count = 0
    try:
        for mc, mi in results:
            source_bucket = mi.bucket_name
            target_action = mc.ai_suggested_category
            
            if not target_action:
                continue
                
            if target_action == "delete":
                target_bucket = b2_account.trash_bucket_name
                if target_bucket:
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, mi.file_name
                    )).start()
                    threading.Thread(target=b2_move_background_task, args=(
                        b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", mi.file_name
                    )).start()
                    mi.bucket_name = target_bucket
                    mi.is_in_sorter = False
                    mc.is_deleted = True
                    mc.category = None
            else:
                target_bucket = b2_account.bucket_name
                if target_action == "uncategorized":
                    mc.category = None
                    mc.is_deleted = False
                    mi.is_in_sorter = False
                else:
                    file_info = {"category": target_action}
                    if source_bucket != target_bucket:
                        threading.Thread(target=b2_move_background_task, args=(
                            b2_account.key_id, b2_account.application_key, source_bucket, target_bucket, mi.file_name, file_info
                        )).start()
                        threading.Thread(target=b2_move_background_task, args=(
                            b2_account.key_id, b2_account.application_key, f"{source_bucket}-thumbs", f"{target_bucket}-thumbs", mi.file_name, file_info
                        )).start()
                        mi.bucket_name = target_bucket
                    else:
                        def update_metadata_task(key_id, app_key, bucket, file_name, info):
                            try:
                                client = B2Client(key_id, app_key)
                                client.update_file_info(bucket, file_name, info)
                            except Exception as e:
                                logger.error(f"Metadata update failed for {file_name}: {e}")

                        threading.Thread(target=update_metadata_task, args=(
                            b2_account.key_id, b2_account.application_key, target_bucket, mi.file_name, file_info
                        )).start()
                        
                    mc.category = target_action
                    mc.is_deleted = False
                    mi.is_in_sorter = False
                    
            mc.ai_status = "approved"
            count += 1
            
        db.commit()
        return {"status": "ok", "count": count}
    except Exception as e:
        db.rollback()
        logger.exception("Approve all error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/classification/reject-all")
def reject_all_suggestions(db: Session = Depends(get_db)):
    """ Resets is_in_sorter=False and clears ai_status for all pending items. """
    try:
        results = db.query(MediaClassification, MediaItem).join(
            MediaItem, MediaClassification.file_name == MediaItem.file_name
        ).filter(MediaClassification.ai_status == "pending", MediaItem.is_in_sorter == True).all()
        
        count = 0
        for mc, mi in results:
            mc.ai_status = None
            mc.ai_suggested_category = None
            mc.ai_error = None
            mi.is_in_sorter = False
            count += 1
            
        db.commit()
        return {"status": "ok", "count": count}
    except Exception as e:
        db.rollback()
        logger.exception("Reject all error")
        raise HTTPException(status_code=500, detail=str(e))
