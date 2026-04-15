import time
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .database import SessionLocal
from .models import MediaItem, B2Account, MediaClassification, CategoryDefinition
from .utils.b2_client import B2Client
import random
import logging

logger = logging.getLogger(__name__)

class SlideshowController:
    def __init__(self):
        self._b2_clients = {}  # Cache: {account_id: B2Client}
        self._decks = {}  # Cache: {(session_id, folder, category): [shuffled_ids]}
        
        # v7.3/v7.4 System Control State
        self.master_switch = True
        self.active_sessions = {} # {session_id: {"last_seen": float, "ip": str, "user_agent": str, "device_name": str, "folder": str, "category": str}}
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
        """Returns direct subdirectories under the given parent_path. Looks in both synced items and recent classifications."""
        # Get active account - Be less restrictive, pick any active account that has items
        b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_acc:
            logger.warning("get_folders: No active B2 account found.")
            return []

        # 1. Folders from synced MediaItems
        query_mi = db.query(MediaItem.file_name).filter(MediaItem.bucket_name == b2_acc.bucket_name)
        
        # 2. Folders from categorized MediaClassifications (Level 2 Instant Visibility)
        query_mc = db.query(MediaClassification.file_name).filter(MediaClassification.is_deleted == False)

        if parent_path:
            if not parent_path.endswith('/'):
                parent_path += '/'
            query_mi = query_mi.filter(MediaItem.file_name.like(f"{parent_path}%"))
            query_mc = query_mc.filter(MediaClassification.file_name.like(f"{parent_path}%"))
            
        seen_folders = set()
        
        # Helper to extract next-level folder name
        def add_from_results(results, prefix):
            for row in results:
                file_path = row[0]
                relative_path = file_path[len(prefix):] if (prefix and len(prefix) > 0) else file_path
                parts = relative_path.split('/')
                if len(parts) > 1:
                    seen_folders.add(parts[0])

        items_mi = query_mi.all()
        items_mc = query_mc.all()
        
        logger.info(f"get_folders: Found {len(items_mi)} items in MediaItem and {len(items_mc)} in Classification for path '{parent_path}'")

        add_from_results(items_mi, parent_path)
        add_from_results(items_mc, parent_path)
                
        folders = [{"name": folder, "path": f"{parent_path}{folder}" if parent_path else folder} for folder in sorted(list(seen_folders))]
        logger.info(f"get_folders: identified {len(folders)} unique subfolders.")
        return folders

    def get_all_folders(self, db: Session, bucket_name: str) -> list:
        """Returns a flat list of all unique folder paths in the given bucket."""
        # Query all file names in bucket
        results = db.query(MediaItem.file_name).filter(MediaItem.bucket_name == bucket_name).all()
        
        seen_folders = set()
        for row in results:
            file_path = row[0]
            parts = file_path.split('/')
            if len(parts) > 1:
                # Join all but the last part (filename)
                folder_path = "/".join(parts[:-1])
                seen_folders.add(folder_path)
        
        return sorted(list(seen_folders))

    def get_random_image(self, db: Session, folder: str = None, category: str = None, session_id: str = "default"):
        """Fetches a random image, filtered by folder and category. Uses a 'deck' system per session to avoid repetition."""
        
        # Get active account - Prefer one that is already 'Finished' sync
        b2_acc = db.query(B2Account).filter(B2Account.is_active == True, B2Account.sync_status == 'Finished').first()
        if not b2_acc:
            # Fallback to any active account if none are finished yet
            b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()

        if not b2_acc:
            return None

        folder_prefix = folder
        if folder_prefix and not folder_prefix.endswith('/'):
            folder_prefix += '/'

        deck_key = (session_id, folder_prefix, category)

        # Initialize or refill deck if empty
        if deck_key not in self._decks or not self._decks[deck_key]:
            logger.info(f"Session '{session_id}': Deck empty for key {deck_key}. Refilling...")
            if category:
                # LEVEL 2 INSTANT VISIBILITY: Build deck from classifications table
                query = db.query(MediaClassification.file_name).filter(
                    MediaClassification.category == category,
                    MediaClassification.is_deleted == False
                )
                if folder_prefix:
                    query = query.filter(MediaClassification.file_name.like(f"{folder_prefix}%"))
                
                all_items = [row[0] for row in query.all()]
                
                # V14.1 fallback: Try without accents if empty
                if not all_items:
                    alt_category = category.lower().replace('ó', 'o').replace('ő', 'o').replace('ö', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u').replace('ü', 'u')
                    if alt_category != category:
                        logger.info(f"Retrying category query with fallback: {alt_category}")
                        query = db.query(MediaClassification.file_name).filter(
                            MediaClassification.category == alt_category,
                            MediaClassification.is_deleted == False
                        )
                        if folder_prefix:
                            query = query.filter(MediaClassification.file_name.like(f"{folder_prefix}%"))
                        all_items = [row[0] for row in query.all()]

                logger.info(f"Building category deck for '{category}'. Found {len(all_items)} items in DB.")
            else:
                # Standard shuffle
                query = db.query(MediaItem.id).outerjoin(
                    MediaClassification, MediaItem.file_name == MediaClassification.file_name
                ).filter(
                    MediaItem.bucket_name == b2_acc.bucket_name,
                    or_(MediaClassification.is_deleted == False, MediaClassification.is_deleted == None)
                )
                if folder_prefix:
                    query = query.filter(MediaItem.file_name.like(f"{folder_prefix}%"))
                
                all_items = [row[0] for row in query.all()]
                logger.info(f"Building folder deck for '{folder_prefix or 'Root'}'. Found {len(all_items)} items in DB.")
            
            if not all_items:
                logger.warning(f"No results found for session '{session_id}' with key {deck_key}")
                return None
            
            random.shuffle(all_items)
            self._decks[deck_key] = all_items
            logger.info(f"Deck refilled for session '{session_id}' with {len(all_items)} items. (Shuffled)")

        # Pop from deck
        next_val = self._decks[deck_key].pop(0)

        # Retrieve media_item or create virtual one
        is_virtual = False
        if category:
            file_name = next_val
            media_item = db.query(MediaItem).filter(MediaItem.file_name == file_name).first()
            if not media_item:
                is_virtual = True
                from .models import MediaItem as MediaItemModel
                media_item = MediaItemModel(
                    id=f"virtual-{file_name}",
                    file_name=file_name,
                    bucket_name=b2_acc.bucket_name,
                    b2_account_id=b2_acc.id
                )
            else:
                # LEVEL 2 VISIBILITY: If categorized, it's already at the target bucket (or being moved there)
                # Override stale bucket info from DB to avoid 404s if the sync hasn't run yet
                if media_item.bucket_name != b2_acc.bucket_name:
                    logger.info(f"Overriding stale bucket for {media_item.file_name}: {media_item.bucket_name} -> {b2_acc.bucket_name}")
                    media_item.bucket_name = b2_acc.bucket_name
        else:
            media_item = db.query(MediaItem).filter(MediaItem.id == next_val).first()
        
        if not media_item or not media_item.b2_account_id:
            logger.error(f"Failed to retrieve media item for key {next_val}. (virtual={is_virtual})")
            return None
            
        client, b2_acc_item = self._get_b2_client(db, media_item.b2_account_id)
        if not client or not b2_acc_item:
            logger.error(f"Failed to get B2 client for account {media_item.b2_account_id}")
            return None
            
        logger.info(f"Serving {'VIRTUAL ' if is_virtual else ''}image: {media_item.file_name} from bucket {media_item.bucket_name}")
        
        display_url = client.get_download_url(
            media_item.bucket_name, 
            media_item.file_name, 
            b2_acc_item.cloudflare_proxy_url
        )
        
        caption = self._format_caption(media_item.file_name)
        
        class_item = db.query(MediaClassification).filter(MediaClassification.file_name == media_item.file_name).first()
        file_category = class_item.category if class_item and not class_item.is_deleted else None
        category_info = None
        if file_category:
            cat_def = db.query(CategoryDefinition).filter(CategoryDefinition.name == file_category).first()
            if cat_def:
                category_info = {
                    "name": cat_def.name,
                    "display_name": cat_def.display_name,
                    "icon": cat_def.icon,
                    "color": cat_def.color
                }
            else:
                category_info = {"name": file_category, "display_name": file_category.capitalize(), "icon": "tag", "color": "#6366f1"}

        return {
            "url": display_url,
            "filename": caption,
            "file_path": media_item.file_name,
            "id": media_item.id,
            "category_info": category_info
        }

    def _format_caption(self, file_path):
        """Converts '2023/12/Xmas/img.jpg' to '2023 - 12 - Xmas'."""
        parts = file_path.split('/')
        if len(parts) > 1:
            return " - ".join(parts[:-1])
        return file_path

    # v7.3/v7.4 System Controls
    def heartbeat(self, session_id: str, client_info: dict) -> bool:
        """Registers a heartbeat and client metadata. Returns False if session should stop."""
        if not self.master_switch:
            return False
        if session_id in self.killed_sessions:
            return False
            
        client_info["last_seen"] = time.time()
        self.active_sessions[session_id] = client_info
        return True

    def get_system_status(self) -> dict:
        """Counts active clients (heartbeat within 10 seconds) and returns their metadata."""
        now = time.time()
        self.active_sessions = {sid: info for sid, info in self.active_sessions.items() if now - info.get("last_seen", 0) < 10.0}
        
        return {
            "master_switch": self.master_switch,
            "active_clients": len(self.active_sessions),
            "sessions": self.active_sessions
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
        
# Global singleton instance
controller = SlideshowController()
