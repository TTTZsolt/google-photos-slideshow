import time
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .database import SessionLocal
from .models import MediaItem, B2Account
from .utils.b2_client import B2Client
import random

logger = logging.getLogger(__name__)

class SlideshowController:
    def __init__(self):
        self._b2_clients = {}  # Cache: {account_id: B2Client}
        self._decks = {}  # Cache: {(session_id, folder): [shuffled_ids]}
        
        # v7.3 System Control State
        self.master_switch = True
        self.active_sessions = {} # {session_id: timestamp_float}
        self.killed_sessions = set() # {session_id}

    def _get_b2_client(self, db: Session, account_id: int):
        if account_id not in self._b2_clients:
            b2_acc = db.query(B2Account).filter(B2Account.id == account_id).first()
            if not b2_acc:
                return None, None
            self._b2_clients[account_id] = B2Client(b2_acc.key_id, b2_acc.application_key)
        
        b2_acc = db.query(B2Account).filter(B2Account.id == account_id).first()
        return self._b2_clients[account_id], b2_acc

    def get_folders(self, db: Session, parent_path: str = None):
        """Returns direct subdirectories under the given parent_path."""
        query = db.query(MediaItem.file_name)
        
        if parent_path:
            # Add trailing slash if not present to ensure we only match inside the folder
            if not parent_path.endswith('/'):
                parent_path += '/'
            query = query.filter(MediaItem.file_name.like(f"{parent_path}%"))
            
        seen_folders = set()
        for row in query.all():
            file_path = row[0]
            
            # If parent_path is '2023/', and file_path is '2023/Nyaralas/kep.jpg'
            # We want to extract 'Nyaralas'
            if parent_path:
                relative_path = file_path[len(parent_path):]
            else:
                relative_path = file_path
                
            parts = relative_path.split('/')
            # If there's more than one part, the first part is a directory
            if len(parts) > 1:
                folder_name = parts[0]
                seen_folders.add(folder_name)
                
        # Return sorted list of dictionaries
        folders = [{"name": folder, "path": f"{parent_path}{folder}" if parent_path else folder} for folder in sorted(list(seen_folders))]
        return folders

    def get_random_image(self, db: Session, folder: str = None, session_id: str = "default"):
        """Fetches a random image, filtered by folder. Uses a 'deck' system per session to avoid repetition."""
        query = db.query(MediaItem)
        
        folder_prefix = folder
        if folder_prefix and not folder_prefix.endswith('/'):
            folder_prefix += '/'

        deck_key = (session_id, folder_prefix)

        # Initialize or refill deck if empty
        if deck_key not in self._decks or not self._decks[deck_key]:
            if folder_prefix:
                query = query.filter(MediaItem.file_name.like(f"{folder_prefix}%"))
            all_ids = [row[0] for row in query.with_entities(MediaItem.id).all()]
            
            if not all_ids:
                return None
            
            random.shuffle(all_ids)
            self._decks[deck_key] = all_ids
            logger.info(f"Refilled deck for session '{session_id}' (folder '{folder_prefix}') with {len(all_ids)} items.")

        # Pop from deck
        next_id = self._decks[deck_key].pop(0)

        media_item = db.query(MediaItem).filter(MediaItem.id == next_id).first()
        
        if not media_item or not media_item.b2_account_id:
            return None
            
        client, b2_acc = self._get_b2_client(db, media_item.b2_account_id)
        if not client or not b2_acc:
            return None
            
        display_url = client.get_download_url(
            b2_acc.bucket_name, 
            media_item.file_name, 
            b2_acc.cloudflare_proxy_url
        )
        
        caption = self._format_caption(media_item.file_name)
        
        return {
            "url": display_url,
            "filename": caption,
            "id": media_item.id
        }

    def _format_caption(self, file_path):
        """Converts '2023/12/Xmas/img.jpg' to '2023 - 12 - Xmas'."""
        parts = file_path.split('/')
        if len(parts) > 1:
            return " - ".join(parts[:-1])
        return file_path

    # v7.3 System Controls
    def heartbeat(self, session_id: str) -> bool:
        """Registers a heartbeat. Returns False if session should stop."""
        if not self.master_switch:
            return False
        if session_id in self.killed_sessions:
            return False
            
        self.active_sessions[session_id] = time.time()
        return True

    def get_system_status(self) -> dict:
        """Counts active clients (heartbeat within 10 seconds)."""
        now = time.time()
        # Clean up old sessions
        self.active_sessions = {sid: ts for sid, ts in self.active_sessions.items() if now - ts < 10.0}
        
        return {
            "master_switch": self.master_switch,
            "active_clients": len(self.active_sessions)
        }
        
    def toggle_master_switch(self) -> bool:
        self.master_switch = not self.master_switch
        return self.master_switch
        
    def kill_all_sessions(self):
        """Moves all current active sessions to the killed set."""
        for session_id in self.active_sessions.keys():
            self.killed_sessions.add(session_id)
        self.active_sessions.clear()
        
# Global singleton instance
controller = SlideshowController()
