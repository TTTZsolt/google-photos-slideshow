import time
import threading
import logging
from sqlalchemy.sql import func
from .database import SessionLocal
from .models import MediaItem

logger = logging.getLogger(__name__)

class SlideshowController:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._last_error = None
        self._b2_clients = {}  # Cache: {account_id: B2Client}
        self._current_image_data = {
            "url": None, 
            "filename": None,
            "interval": 20, 
            "show_filename": False
        }

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def discover_devices(self):
        """Removed as Chromecast integration is disabled."""
        return []

    def start(self, interval: int = 20, show_filename: bool = False):
        if self._thread and self._thread.is_alive():
            logger.warning("Slideshow already running")
            return

        self._stop_event.clear()
        self._current_image_data["interval"] = interval
        self._current_image_data["show_filename"] = show_filename
        self._thread = threading.Thread(target=self._run_loop, args=(interval,))
        self._thread.start()
        logger.info(f"Slideshow loop started (show_filename={show_filename})")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._b2_clients.clear()  # Clear cache on stop
        logger.info("Slideshow stopped")

    def get_current_image_data(self):
        return self._current_image_data

    def _run_loop(self, interval):
        try:
            while not self._stop_event.is_set():
                db = SessionLocal()
                try:
                    # Pick random media item
                    media_item = db.query(MediaItem).order_by(func.random()).first()
                    if not media_item:
                        time.sleep(5)
                        continue

                    # Get image URL from B2
                    if media_item.b2_account_id:
                        from .models import B2Account
                        from .utils.b2_client import B2Client
                        
                        b2_acc = db.query(B2Account).filter(B2Account.id == media_item.b2_account_id).first()
                        if b2_acc:
                            # Reuse or create B2 client
                            if b2_acc.id not in self._b2_clients:
                                self._b2_clients[b2_acc.id] = B2Client(b2_acc.key_id, b2_acc.application_key)
                            
                            client = self._b2_clients[b2_acc.id]
                            display_url = client.get_download_url(b2_acc.bucket_name, media_item.file_name)
                            
                            # Update state - the receiver will poll this
                            self._current_image_data["url"] = display_url
                            self._current_image_data["filename"] = media_item.file_name
                        
                except Exception as e:
                    logger.error(f"Error in slideshow loop: {e}")
                finally:
                    db.close()

                # Wait for interval
                if self._stop_event.wait(interval):
                    break
        
        except Exception as e:
            logger.error(f"Critical error in slideshow loop: {e}")
            self._last_error = f"Error: {str(e)}"
        
        logger.info("Slideshow loop exited")

    def get_last_error(self):
        return self._last_error
