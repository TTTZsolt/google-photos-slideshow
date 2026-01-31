import os
import signal
import subprocess
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from ..slideshow import controller

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/remote")
def get_remote(request: Request):
    return templates.TemplateResponse("remote.html", {"request": request})

@router.post("/remote/start")
def remote_start():
    # Start the slideshow logic with default parameters
    controller.start(interval=20, show_filename=True)
    return {"status": "started"}

@router.post("/remote/stop")
def remote_stop():
    """Panic stop: stops casting and shuts down the server process."""
    # 1. Stop casting (catt)
    try:
        subprocess.run(["catt", "stop"], capture_output=True)
    except Exception:
        pass
    
    # 2. Stop slideshow logic
    controller.stop()
    
    # 3. Shutdown the server process
    # We use a short delay to allow the response to reach the client
    def shutdown():
        import time
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
        
    import threading
    threading.Thread(target=shutdown).start()
    
    return {"status": "shutting_down"}
