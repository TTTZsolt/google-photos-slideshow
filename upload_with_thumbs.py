import os
import sys
import logging
from pathlib import Path
from PIL import Image
import io
from backend.utils.b2_client import B2Client
from backend.database import SessionLocal
from backend.models import B2Account

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Uploader")

def create_thumbnail(image_bytes, max_size=(400, 400)):
    """Creates a thumbnail from bytes and returns the thumbnail bytes."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Maintain aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        # Convert to RGB if necessary (for PNG/WEBP to JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        thumb_io = io.BytesIO()
        img.save(thumb_io, format="JPEG", quality=75, optimize=True)
        return thumb_io.getvalue()

def upload_folder(source_dir, target_bucket_name, account_id=None):
    db = SessionLocal()
    try:
        # 1. Get B2 Account
        if account_id:
            b2_acc = db.query(B2Account).filter(B2Account.id == account_id).first()
        else:
            b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()
        
        if not b2_acc:
            logger.error("No active B2 account found in database.")
            return

        client = B2Client(b2_acc.key_id, b2_acc.application_key)
        thumb_bucket_name = f"{target_bucket_name}-thumbs"
        
        logger.info(f"Starting upload from: {source_dir}")
        logger.info(f"Target Bucket: {target_bucket_name}")
        logger.info(f"Thumb Bucket: {thumb_bucket_name}")

        source_path = Path(source_dir)
        if not source_path.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return

        # 2. Get list of supported extensions
        extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        
        files_to_process = []
        for root, _, files in os.walk(source_dir):
            for file in files:
                if Path(file).suffix.lower() in extensions:
                    files_to_process.append(Path(root) / file)
        
        total_files = len(files_to_process)
        logger.info(f"Found {total_files} images to process.")

        for i, local_file in enumerate(files_to_process, 1):
            # Calculate B2 path (relative to source_dir)
            b2_path = local_file.relative_to(source_path).as_posix()
            
            try:
                logger.info(f"[{i}/{total_files}] Processing: {b2_path}")
                
                with open(local_file, 'rb') as f:
                    file_bytes = f.read()

                # A. Upload Original
                client.upload_byte_stream(
                    target_bucket_name,
                    b2_path,
                    file_bytes,
                    content_type="image/jpeg" # B2SDK will refine this
                )
                
                # B. Create and Upload Thumbnail
                thumb_bytes = create_thumbnail(file_bytes)
                client.upload_byte_stream(
                    thumb_bucket_name,
                    b2_path,
                    thumb_bytes,
                    content_type="image/jpeg"
                )
                
                logger.info(f"    Success: Original and Thumbnail uploaded.")

            except Exception as e:
                logger.error(f"    Failed to process {b2_path}: {e}")

        logger.info("Upload process finished.")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python upload_with_thumbs.py <source_directory> <target_bucket_name>")
        print("Example: python upload_with_thumbs.py \"C:/Photos/2024\" kepek02")
        sys.exit(1)
    
    src = sys.argv[1]
    target = sys.argv[2]
    upload_folder(src, target)
