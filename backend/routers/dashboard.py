from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import B2Account, MediaItem
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

class B2ConnectRequest(BaseModel):
    key_id: str
    application_key: str
    bucket_name: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    b2_accounts = db.query(B2Account).all()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "b2_accounts": b2_accounts
    })

@router.get("/receiver")
def get_receiver(request: Request):
    import datetime
    client_ip = request.client.host
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-4]
    print(f"[{now}] DEBUG: Connection attempt to /receiver from IP: {client_ip}")
    return templates.TemplateResponse("receiver.html", {"request": request})

@router.post("/b2/connect")
def connect_b2(req: B2ConnectRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Simple check if already exists
    account = db.query(B2Account).filter(B2Account.key_id == req.key_id).first()
    if not account:
        account = B2Account(
            key_id=req.key_id,
            application_key=req.application_key,
            bucket_name=req.bucket_name
        )
        db.add(account)
    else:
        account.application_key = req.application_key
        account.bucket_name = req.bucket_name
    
    db.commit()
    db.refresh(account)
    
    # Auto-trigger sync
    from ..worker import sync_b2_worker
    background_tasks.add_task(sync_b2_worker, account.id)
    
    return {"message": "B2 Bucket connected & Sync started successfully"}

@router.post("/b2/sync/{account_id}")
def trigger_b2_sync(account_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from ..worker import sync_b2_worker
    background_tasks.add_task(sync_b2_worker, account_id)
    return {"message": f"B2 Sync triggered for account {account_id}"}

@router.post("/b2/delete/{account_id}")
def delete_b2_account(account_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import delete
    account = db.query(B2Account).filter(B2Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="B2 Account not found")
    
    # Delete associated media items
    db.execute(delete(MediaItem).where(MediaItem.b2_account_id == account_id))
    db.delete(account)
    db.commit()
    return {"message": "B2 Bucket and associated index deleted successfully"}

# Singleton controller
from ..slideshow import SlideshowController
controller = SlideshowController()

@router.post("/slideshow/start")
def start_slideshow(interval: int = 20, show_filename: bool = False, db: Session = Depends(get_db)):
    # Check if there are any media items
    count = db.query(MediaItem).count()
    if count == 0:
        raise HTTPException(status_code=400, detail="No media items found. Please sync your B2 bucket first!")
    
    controller.start(interval, show_filename)
    return {"message": f"Slideshow started with {interval}s interval (show_filename={show_filename})"}

@router.post("/slideshow/stop")
def stop_slideshow():
    controller.stop()
    return {"message": "Slideshow stopped"}

@router.get("/slideshow/current-image")
def get_current_image():
    return controller.get_current_image_data()

@router.get("/slideshow/status")
def get_slideshow_status():
    return {
        "running": controller.is_running(),
        "error": controller.get_last_error()
    }

@router.post("/reset")
def reset_database():
    from ..database import Base, engine
    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "System reset successfully"}
