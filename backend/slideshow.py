import time
import threading
import logging
import random
import pychromecast
from sqlalchemy.sql import func
from .database import SessionLocal
from .models import MediaItem, Account
from .auth import get_credentials_for_account
from .utils.google_photos import GooglePhotosClient

logger = logging.getLogger(__name__)

class SlideshowController:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._current_device = None
        self._last_error = None

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def discover_devices(self):
        """Returns a list of friendly names of discovered Cast devices."""
        services, browser = pychromecast.discovery.discover_chromecasts()
        pychromecast.discovery.stop_discovery(browser)
        return [service.friendly_name for service in services]

    def start(self, device_name: str, interval: int = 20):
        if self._thread and self._thread.is_alive():
            logger.warning("Slideshow already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(device_name, interval))
        self._thread.start()
        logger.info(f"Slideshow started on {device_name}")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        logger.info("Slideshow stopped")

    def _run_loop(self, device_name, interval):
        try:
            # Connect to Chromecast
            # Retry discovery a few times
            chromecasts = []
            for _ in range(3):
                chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=[device_name])
                if chromecasts:
                    break
                logger.warning(f"Device {device_name} not found yet, retrying...")
                time.sleep(1)

            if not chromecasts:
                # Fallback: list all devices to debug
                services, browser = pychromecast.discovery.discover_chromecasts()
                found_names = [s.friendly_name for s in services]
                pychromecast.discovery.stop_discovery(browser)
                logger.error(f"Could not find device '{device_name}'. Found devices: {found_names}")
                self._last_error = f"Device '{device_name}' not found. Check network."
                return
            
            cast = chromecasts[0]
            cast.wait()
            logger.info(f"Connected to {cast.name}")

            mc = cast.media_controller

            while not self._stop_event.is_set():
                db = SessionLocal()
                try:
                    # 1. Pick random media item
                    media_item = db.query(MediaItem).order_by(func.random()).first()
                    if not media_item:
                        logger.warning("No media items found in index. Skipping...")
                        time.sleep(5)
                        continue

                    # 2. Refresh Base URL (it expires!)
                    creds = get_credentials_for_account(db, media_item.account_id)
                    if not creds:
                        logger.error(f"No credentials for account {media_item.account_id}")
                        continue
                    
                    client = GooglePhotosClient(creds)
                    fresh_item = client.get_media_item(media_item.id)
                    image_url = fresh_item['baseUrl']
                    
                    # Update DB with fresh URL just in case
                    media_item.base_url = image_url
                    db.commit()

                # 3. Cast
                    # Google Photos images usually need some parameters to size/crop? 
                    #Appending '=w1920-h1080' helps for TV resolution.
                    display_url = f"{image_url}=w1920-h1080"
                    
                    logger.info(f"Casting: {media_item.filename} (Mime: {media_item.mime_type})")
                    logger.info(f"URL: {display_url}")
                    
                    # Default to jpeg if none
                    content_type = media_item.mime_type if media_item.mime_type else 'image/jpeg'
                    mc.play_media(display_url, content_type)
                    mc.block_until_active()
                    
                except Exception as e:
                    logger.error(f"Error in slideshow loop: {e}")
                finally:
                    db.close()

                # Wait for interval or stop signal
                if self._stop_event.wait(interval):
                    break
        
        except Exception as e:
            logger.error(f"Critical error in slideshow loop: {e}")
            self._last_error = f"Error: {str(e)}"
        
        # Cleanup
        if 'cast' in locals() and cast:
            cast.quit_app()

    def get_last_error(self):
        return self._last_error
