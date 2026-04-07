from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from typing import Optional
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import B2Account, MediaItem, FlaggedImage
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

class B2ConnectRequest(BaseModel):
    key_id: str
    application_key: str
    bucket_name: str
    archive_bucket_name: str
    source_bucket_name: str
    trash_bucket_name: str
    cloudflare_proxy_url: Optional[str] = None

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

@router.get("/b2/accounts")
def get_b2_accounts(db: Session = Depends(get_db)):
    accounts = db.query(B2Account).all()
    return accounts

@router.get("/receiver")
def get_receiver(request: Request):
    import datetime
    client_ip = request.client.host
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-4]
    print(f"[{now}] DEBUG: Connection attempt to /receiver from IP: {client_ip}")
    return templates.TemplateResponse("receiver.html", {"request": request})

@router.get("/trash")
def get_trash_page(request: Request):
    return templates.TemplateResponse("trash.html", {"request": request})

@router.post("/b2/connect")
def connect_b2(req: B2ConnectRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Simple check if already exists
    account = db.query(B2Account).filter(B2Account.key_id == req.key_id).first()
    if not account:
        account = B2Account(
            key_id=req.key_id,
            application_key=req.application_key,
            bucket_name=req.bucket_name,
            archive_bucket_name=req.archive_bucket_name,
            source_bucket_name=req.source_bucket_name,
            trash_bucket_name=req.trash_bucket_name,
            cloudflare_proxy_url=req.cloudflare_proxy_url
        )
        db.add(account)
    else:
        account.application_key = req.application_key
        account.bucket_name = req.bucket_name
        account.archive_bucket_name = req.archive_bucket_name
        account.source_bucket_name = req.source_bucket_name
        account.trash_bucket_name = req.trash_bucket_name
        account.cloudflare_proxy_url = req.cloudflare_proxy_url
    
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

# Use shared singleton controller
from ..slideshow import controller

@router.get("/api/system/status")
def get_system_status():
    return controller.get_system_status()

@router.post("/api/system/toggle")
def toggle_system():
    return {"master_switch": controller.toggle_master_switch()}
    
@router.post("/api/system/kill_all")
def kill_all_sessions():
    controller.kill_all()
    return {"message": "All sessions terminated"}

# --- IMAGE FLAGGING / RETOUCH QUEUE ---

class FlagImageRequest(BaseModel):
    file_name: str

@router.post("/api/flags")
def flag_image(req: FlagImageRequest, db: Session = Depends(get_db)):
    # Check if already flagged
    existing = db.query(FlaggedImage).filter(FlaggedImage.file_name == req.file_name).first()
    if existing:
        return {"message": "Már megjelölve."}
    
    new_flag = FlaggedImage(file_name=req.file_name)
    db.add(new_flag)
    db.commit()
    db.refresh(new_flag)
    return {"message": "Sikeresen megjelölve javításra!"}

@router.get("/api/flags")
def get_flagged_images(db: Session = Depends(get_db)):
    # Get all flagged images descending by date
    from sqlalchemy import desc
    flags = db.query(FlaggedImage).order_by(desc(FlaggedImage.flagged_at)).all()
    return [{"id": f.id, "file_name": f.file_name, "flagged_at": f.flagged_at} for f in flags]

@router.delete("/api/flags/{flag_id}")
def resolve_flagged_image(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(FlaggedImage).filter(FlaggedImage.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Jelölés nem található.")
    db.delete(flag)
    db.commit()
    return {"message": "Törölve a listáról."}

@router.post("/api/heartbeat/{session_id}")
def heartbeat(request: Request, session_id: str, device_name: str = None, folder: str = None, category: str = None):
    # Extract client metadata
    client_ip = request.client.host if request.client else "Unknown"
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Simplify common user agents for UI display
    ua_str = "Készülék"
    if "Android" in user_agent: ua_str = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent: ua_str = "iOS"
    elif "Windows" in user_agent: ua_str = "Windows PC"
    elif "Macintosh" in user_agent: ua_str = "Mac"
    elif "CrOS" in user_agent: ua_str = "Chrome OS"
    elif "SmartTV" in user_agent or "Tizen" in user_agent or "Web0S" in user_agent: ua_str = "Smart TV"
    
    client_info = {
        "ip": client_ip,
        "user_agent": ua_str,
        "device_name": device_name or ua_str,
        "folder": folder or "Összes (Root)",
        "category": category or "Nincs szűrés"
    }
    
    is_alive = controller.heartbeat(session_id, client_info)
    if not is_alive:
        raise HTTPException(status_code=403, detail="Session stopped by administrator")
    return {"status": "ok"}

@router.get("/api/folders")
def get_folders(parent: str = None, db: Session = Depends(get_db)):
    """Returns subdirectories under the given parent directory."""
    try:
        folders = controller.get_folders(db, parent_path=parent)
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/folders/all")
def get_all_folders(db: Session = Depends(get_db)):
    """Returns a flat list of all unique folder paths in the active bucket (kepek02)."""
    try:
        # Prefer an account that is already 'Finished' sync
        b2_acc = db.query(B2Account).filter(B2Account.is_active == True, B2Account.sync_status == 'Finished').first()
        if not b2_acc:
            # Fallback to any active account
            b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
            
        if not b2_acc:
            return {"folders": []}
        
        from .dashboard import controller
        folders = controller.get_all_folders(db, b2_acc.bucket_name)
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/media/random")
def get_random_media(folder: str = None, category: str = None, session_id: str = "default", db: Session = Depends(get_db)):
    """Returns a random media item, optionally filtered by folder, category and session."""
    try:
        media_item = controller.get_random_image(db, folder=folder, category=category, session_id=session_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="No media items found for the given folder.")
        return media_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
def reset_database():
    from ..database import Base, engine
    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "System reset successfully"}

def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@router.get("/slideshow/devices")
def scan_devices():
    import subprocess
    import re
    try:
        # Kill any zombie catt processes before scanning
        subprocess.run(["pkill", "-f", "catt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Run catt scan and capture output with strict timeout
        result = subprocess.run(["catt", "scan"], capture_output=True, text=True, timeout=12)
        output = result.stdout
        
        # Parse output: "192.168.1.181 - Nappali - Google TV"
        devices = []
        for line in output.splitlines():
            if " - " in line:
                parts = line.split(" - ")
                if len(parts) >= 2:
                    device_name = parts[1].strip()
                    if device_name not in devices:
                        devices.append(device_name)
        
        return {"devices": devices}
    except Exception as e:
        print(f"DEBUG: CATT scan error: {e}")
        return {"devices": [], "error": str(e)}

@router.post("/slideshow/cast")
def cast_to_device(device_name: str, request: Request):
    import subprocess
    import time
    from urllib.parse import urlencode

    local_ip = get_local_ip()
    port = request.url.port or 8080
    
    # Extract query params from this POST request
    query_params = dict(request.query_params)
    
    # We will pass the device_name to the receiver so the dashboard can identify the TV by name
    # We don't remove it, we just make sure TS and start_global are appended
    query_params["ts"] = str(int(time.time()))
    query_params["start_global"] = "true"
    
    query_string = urlencode(query_params)
    receiver_url = f"http://{local_ip}:{port}/receiver?{query_string}"
    
    print(f"DEBUG: Casting {receiver_url} to device: {device_name}")
    
    try:
        # Stop any existing cast/catt process before starting new one
        subprocess.run(["pkill", "-f", "catt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Run catt cast_site in background (non-blocking)
        subprocess.Popen(["catt", "-d", device_name, "cast_site", receiver_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"message": f"Casting initiated to {device_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CATT error: {str(e)}")

@router.post("/slideshow/stop-cast")
def stop_casting(device_name: str):
    import subprocess
    print(f"DEBUG: Stopping cast on device: {device_name}")
    try:
        # First kill the local catt process if it's hanging
        subprocess.run(["pkill", "-f", "catt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Then tell the TV to stop with a timeout
        subprocess.run(["catt", "-d", device_name, "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return {"message": f"Casting stopped on {device_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CATT error: {str(e)}")

@router.get("/api/photopea/auth-url")
def get_photopea_auth_url(file_path: str, db: Session = Depends(get_db)):
    from urllib.parse import unquote
    file_path = unquote(file_path)
    
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="No active B2 account found")
        
    from ..utils.b2_client import B2Client
    b2_client = B2Client(b2_account.key_id, b2_account.application_key)
    
    try:
        # Force use_proxy=False because Cloudflare Workers strip or don't forward
        # the B2 ?Authorization= query parameter required to download from private buckets
        url = b2_client.get_download_url(
            b2_account.bucket_name,
            file_path,
            b2_account.cloudflare_proxy_url,
            use_proxy=True
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/photopea/save")
async def photopea_save(request: Request, db: Session = Depends(get_db)):
    """ Endpoint that Photopea calls when the user hits Save. """
    from urllib.parse import unquote
    
    # 1. Parse incoming parameters
    # The image path is passed via query params since Photopea POSTs raw binary data
    file_path = request.query_params.get("file_path")
    print(f"DEBUG PHOTOPEA: Incoming save request for {file_path}")
    if not file_path:
        print("DEBUG PHOTOPEA: Missing file_path")
        raise HTTPException(status_code=400, detail="Missing file_path query parameter")
    
    file_path = unquote(file_path)
    
    # 2. Receive edited binary image data
    # Photopea sends a custom ArrayBuffer where the first 2000 bytes are a JSON string padded with spaces, 
    # and the remaining bytes are the actual image file.
    
    body = await request.body()
    print(f"DEBUG PHOTOPEA: Read total body bytes: {len(body)}")
    
    if not body:
        print("DEBUG PHOTOPEA: Empty body received")
        raise HTTPException(status_code=400, detail="No image data received")
        
    try:
        if len(body) > 2000:
            header = body[:2000].decode('utf-8', errors='ignore')
            print(f"DEBUG PHOTOPEA: Header preview: {header[:150]}...")
            if '{"' in header and '"source"' in header:
                print("DEBUG PHOTOPEA: Slicing Photopea custom ArrayBuffer (removing 2000 bytes)")
                image_bytes = body[2000:]
            else:
                print("DEBUG PHOTOPEA: Header does not contain typical JSON marks. Assuming raw image bytes.")
                image_bytes = body
        else:
            print("DEBUG PHOTOPEA: Body is too small to be a padded JSON. Using raw.")
            image_bytes = body
            
    except Exception as e:
        print(f"DEBUG PHOTOPEA: Error slicing payload: {e}")
        import traceback
        traceback.print_exc()
        image_bytes = body
    
    print(f"DEBUG PHOTOPEA: Final image_bytes length: {len(image_bytes)}")
    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="No image data received after slicing")
    
    # 3. Retrieve active B2 Account
    b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
    if not b2_account:
        raise HTTPException(status_code=500, detail="No active B2 account found")
    
    if not b2_account.archive_bucket_name:
        raise HTTPException(status_code=400, detail="No Archive Bucket configured for this B2 Account.")
        
    # 4. Initialize B2 Client
    from ..utils.b2_client import B2Client
    b2_client = B2Client(b2_account.key_id, b2_account.application_key)
    
    try:
        # 5. Determine new file name
        # Ex: "2023/Nyaralas/img.jpg" -> "2023/Nyaralas/img-szerkesztett.jpg"
        parts = file_path.rsplit('.', 1)
        if len(parts) == 2:
            new_file_path = f"{parts[0]}-szerkesztett.{parts[1]}"
        else:
            new_file_path = f"{file_path}-szerkesztett.jpg"
            
        print(f"DEBUG PHOTOPEA: Uploading to {new_file_path} in bucket {b2_account.bucket_name}")
        b2_client.upload_byte_stream(
            bucket_name=b2_account.bucket_name,
            file_name=new_file_path,
            file_bytes=image_bytes,
            content_type="image/jpeg" # Photopea saves as JPG by default based on our format setting
        )
        print("DEBUG PHOTOPEA: Upload successful.")
        
        # 7. Move Original image to Archive Bucket
        try:
            print(f"DEBUG PHOTOPEA: Moving {file_path} to {b2_account.archive_bucket_name}")
            b2_client.move_file(
                source_bucket_name=b2_account.bucket_name,
                dest_bucket_name=b2_account.archive_bucket_name,
                file_name=file_path
            )
        except Exception as move_err:
            print(f"DEBUG B2 Move Error: {str(move_err)}")
            # Even if moving fails (e.g., permission issue), we shouldn't fail the whole save
            # We'll just print the error and continue to remove it from the queue
        
        # 8. Remove from Retouch Queue (FlaggedImage table)
        from sqlalchemy import delete
        db.execute(delete(FlaggedImage).where(FlaggedImage.file_name == file_path))
        db.commit()
        
        # 9. Return success back to Photopea iFrame
        return {"message": "Success", "saved": file_path}
        
    except Exception as e:
        print(f"DEBUG Photopea Save Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
