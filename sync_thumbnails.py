import logging
import io
from PIL import Image
from backend.utils.b2_client import B2Client
from backend.database import SessionLocal
from backend.models import B2Account

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ThumbSync")

def create_thumbnail(image_bytes, max_size=(400, 400)):
    """Creates a thumbnail from bytes and returns the thumbnail bytes."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            thumb_io = io.BytesIO()
            img.save(thumb_io, format="JPEG", quality=75, optimize=True)
            return thumb_io.getvalue()
    except Exception as e:
        logger.error(f"Thumbnail creation error: {e}")
        return None

def sync_all_thumbnails():
    db = SessionLocal()
    try:
        b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_acc:
            logger.error("No active B2 account found.")
            return

        client = B2Client(b2_acc.key_id, b2_acc.application_key)
        
        # Buckets to sync
        buckets = [
            b2_acc.source_bucket_name,
            b2_acc.bucket_name,
            b2_acc.trash_bucket_name,
            b2_acc.archive_bucket_name
        ]
        # Filter out None values
        buckets = [b for b in buckets if b]

        for main_bucket in buckets:
            thumb_bucket = f"{main_bucket}-thumbs"
            logger.info(f"--- Syncing thumbnails for: {main_bucket} -> {thumb_bucket} ---")

            try:
                # 1. Get existing thumbnails to avoid duplicates
                logger.info(f"Listing existing thumbnails in {thumb_bucket}...")
                existing_thumbs = set()
                try:
                    for file_version in client.list_files(thumb_bucket):
                        existing_thumbs.add(file_version.file_name)
                except:
                    logger.warning(f"Could not list {thumb_bucket}. It might be empty or not exist yet.")
                
                logger.info(f"Found {len(existing_thumbs)} existing thumbnails.")

                # 2. List all original files to count them
                logger.info(f"Scanning {main_bucket} for images...")
                all_files = []
                for file_version in client.list_files(main_bucket):
                    file_name = file_version.file_name
                    ext = file_name.lower().split('.')[-1]
                    if ext in ['jpg', 'jpeg', 'png', 'webp']:
                        all_files.append(file_name)
                
                total_images = len(all_files)
                logger.info(f"Found {total_images} total images in bucket.")

                # 3. Process missing thumbnails with progress indicator
                new_count = 0
                skip_count = 0
                for i, file_name in enumerate(all_files, 1):
                    # Skip if thumbnail already exists
                    if file_name in existing_thumbs:
                        skip_count += 1
                        if i % 50 == 0: # Print skip summary every 50 to avoid spam
                            print(f"  [{i}/{total_images}] Skipping (already exists)...", end="\r")
                        continue
                    
                    print(f"  [{i}/{total_images}] Generating: {file_name[:50]}...", end="\r")
                    
                    try:
                        # Download, Resize, Upload
                        url = client.get_download_url(main_bucket, file_name, use_proxy=False)
                        import requests
                        resp = requests.get(url)
                        if resp.status_code == 200:
                            thumb_bytes = create_thumbnail(resp.content)
                            if thumb_bytes:
                                client.upload_byte_stream(thumb_bucket, file_name, thumb_bytes)
                                new_count += 1
                        else:
                            logger.error(f"\n    Failed to download {file_name}: {resp.status_code}")
                    except Exception as e:
                        logger.error(f"\n    Error processing {file_name}: {e}")

                print(f"\n--- Finished {main_bucket} ---")
                logger.info(f"Summary: {new_count} created, {skip_count} skipped, {total_images} total.")

            except Exception as e:
                logger.error(f"Error syncing bucket {main_bucket}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    sync_all_thumbnails()
