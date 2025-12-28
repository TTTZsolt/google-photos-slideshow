import time
import threading
import logging
import random
import pychromecast
from sqlalchemy.sql import func
from .database import SessionLocal
from .models import MediaItem

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

                    # 2. Get image URL (Google or B2)
                    display_url = None
                    file_info = ""

                    if media_item.b2_account_id:
                        from .models import B2Account
                        from .utils.b2_client import B2Client
                        b2_acc = db.query(B2Account).filter(B2Account.id == media_item.b2_account_id).first()
                        if not b2_acc:
                            logger.error(f"B2 account {media_item.b2_account_id} not found")
                            continue
                        
                        client = B2Client(b2_acc.key_id, b2_acc.application_key)
                        display_url = client.get_download_url(b2_acc.bucket_name, media_item.file_name)
                        file_info = media_item.file_name
                    else:
                        logger.error(f"Media item {media_item.id} has no B2 account associated")
                        continue

                # 3. Cast
                    from datetime import datetime
                    now = datetime.now().strftime("%H:%M:%S.%f")[:-4]
                    print(f"[{now}] DEBUG: Initializing cast for: {file_info}")
                    logger.info(f"Casting: {file_info}")
                    content_type = media_item.mime_type if media_item.mime_type else 'image/jpeg'
                    mc.play_media(display_url, content_type)
                    
                    # Wait for the Chromecast to acknowledge and start loading
                    print(f"[{now}] DEBUG: Waiting for TV to start loading...")
                    mc.block_until_active(timeout=15)
                    
                    # Final check status for logs
                    status = mc.status
                    print(f"[{now}] DEBUG: Cast status: {status.player_state}")
                    logger.info(f"Cast status: {status.player_state}")
                    
                except Exception as e:
                    now = datetime.now().strftime("%H:%M:%S.%f")[:-4]
                    print(f"[{now}] ERROR in slideshow loop: {e}")
                    logger.error(f"Error in slideshow loop: {e}")
                    self._last_error = f"Loop error: {str(e)}"
                finally:
                    db.close()

                # Wait for interval or stop signal
                now = datetime.now().strftime("%H:%M:%S.%f")[:-4]
                print(f"[{now}] DEBUG: Waiting {interval} seconds...")
                if self._stop_event.wait(interval):
                    print(f"[{now}] DEBUG: Stop event received, exiting loop.")
                    break
        
        except Exception as e:
            logger.error(f"Critical error in slideshow loop: {e}")
            self._last_error = f"Error: {str(e)}"
        
        # Cleanup
        if 'cast' in locals() and cast:
            cast.quit_app()

    def get_last_error(self):
        return self._last_error
