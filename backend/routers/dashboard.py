from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Account

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    return templates.TemplateResponse("index.html", {"request": request, "accounts": accounts})

@router.post("/sync/{account_id}")
def trigger_sync(account_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from ..worker import sync_account_worker
    background_tasks.add_task(sync_account_worker, account_id)
    return {"message": f"Sync triggered for account {account_id}"} # Trigger worker

# Singleton controller
from ..slideshow import SlideshowController
controller = SlideshowController()

@router.get("/devices")
def list_devices():
    return {"devices": controller.discover_devices()}

@router.post("/slideshow/start")
def start_slideshow(device_name: str = "Family Room TV", interval: int = 20):
    # In real app, receive JSON body
    controller.start(device_name, interval)
    return {"message": f"Slideshow started on {device_name}"}

@router.post("/slideshow/stop")
def stop_slideshow():
    controller.stop()
    return {"message": "Slideshow stopped"}

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
