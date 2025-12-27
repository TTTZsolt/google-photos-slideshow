from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from ..database import SessionLocal, engine
from ..auth import create_or_update_account, SCOPES
from ..models import Base
import os

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Allow insecure transport for local dev (HTTP)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope validation (Google adds 'openid' automatically)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Resolve path relative to backend root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")

@router.get("/login")
def login(request: Request):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "client_secrets.json not found. Please add it to the backend root directory."}

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=str(request.url_for('auth_callback'))
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # In a real app, store state in session to validate later
    return RedirectResponse(authorization_url)

@router.get("/callback")
def auth_callback(request: Request, background_tasks: BackgroundTasks, code: str = None, error: str = None, db: Session = Depends(get_db)):
    if error:
        return {"error": error}
        
    if not code:
        return {"error": "No code provided"}
        
    try:
        if not os.path.exists(CLIENT_SECRETS_FILE):
             return {"error": "client_secrets.json missing"}

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=str(request.url_for('auth_callback'))
        )
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        account = create_or_update_account(db, creds)
        
        # Trigger sync immediately
        from ..worker import sync_account_worker
        background_tasks.add_task(sync_account_worker, account.id)

        return RedirectResponse(url="/") # Redirect to dashboard
    except Exception as e:
        import traceback
        return {"error": f"Internal Error: {str(e)}", "trace": traceback.format_exc()}
