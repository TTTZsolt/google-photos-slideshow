import json
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from .models import Account

SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly', 'https://www.googleapis.com/auth/userinfo.email']

def get_credentials_for_account(db: Session, account_id: int) -> Credentials:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return None
    
    creds_data = json.loads(account.credentials_json)
    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
    
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update DB with new token
        account.credentials_json = creds.to_json()
        db.commit()
        db.refresh(account)
        
    return creds

def create_or_update_account(db: Session, creds: Credentials) -> Account:
    # Use the credentials to get the user's email
    from googleapiclient.discovery import build
    service = build('oauth2', 'v2', credentials=creds)
    user_info = service.userinfo().get().execute()
    email = user_info['email']
    
    account = db.query(Account).filter(Account.email == email).first()
    if not account:
        account = Account(email=email, credentials_json=creds.to_json())
        db.add(account)
    else:
        account.credentials_json = creds.to_json()
        account.is_active = True
    
    db.commit()
    db.refresh(account)
    return account
