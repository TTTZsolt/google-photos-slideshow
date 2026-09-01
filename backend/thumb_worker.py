import io
import logging
from datetime import datetime, time as dt_time
from PIL import Image

from .database import SessionLocal
from .models import MediaItem, B2Account

logger = logging.getLogger(__name__)


def _generate_and_upload_thumbnail(client, source_bucket, thumb_bucket_name, file_name):
    downloaded_file = source_bucket.download_file_by_name(file_name)
    img_data = io.BytesIO()
    downloaded_file.save(img_data)
    img_data.seek(0)

    img = Image.open(img_data)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        alpha = img.convert('RGBA').split()[-1]
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=alpha)
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail((400, 400), Image.Resampling.LANCZOS)

    out_data = io.BytesIO()
    img.save(out_data, format="JPEG", quality=85)
    file_bytes = out_data.getvalue()

    client.upload_byte_stream(
        bucket_name=thumb_bucket_name,
        file_name=file_name,
        file_bytes=file_bytes,
        content_type="image/jpeg"
    )


def generate_missing_thumbnails(b2_account_id: int = None, ignore_time=False, max_test_items=None):
    """
    Onjavito thumbnail-potlas: minden olyan vodorhoz, ahol jelenleg vannak
    indexelt kepek (media_items.bucket_name szerint - a fo vodor ES a Lomtar
    is ide tartozik, barmi mas is, amit a sync epp hasznal), osszeveti a
    kepek listajat a hozzajuk tartozo "-thumbs" vodor tartalmaval, es minden
    hianyzo thumbnailt ujra letrehoz a fo kepbol.

    Ez a biztositek arra, ha egy mozgatas (pl. Lomtarba helyezes) kozben a
    thumbnail-resz atmenetileg elhasal (halozati hiba, B2 throttling stb.) -
    igy sosem marad tartosan "fekete" (hianyzo thumbnailu) kep a feluleten,
    mert a legkozelebbi szinkron automatikusan potolja.
    """
    from .utils.b2_client import B2Client

    logger.info("Starting thumbnail self-heal job...")

    start_time = dt_time(2, 8)
    end_time = dt_time(4, 30)

    if not ignore_time:
        current_time = datetime.now().time()
        if not (start_time <= current_time <= end_time):
            logger.info(f"Not within time window ({start_time} - {end_time}), skipping.")
            return 0

    db = SessionLocal()
    try:
        if b2_account_id:
            b2_acc = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
        else:
            b2_acc = db.query(B2Account).filter(B2Account.is_active == True).first()

        if not b2_acc:
            logger.warning("No B2Account configured, skipping thumbnail self-heal.")
            return 0

        client = B2Client(b2_acc.key_id, b2_acc.application_key)

        # Every bucket that currently has indexed images for this account -
        # not hardcoded to just the main bucket, so the Lomtar (and any other
        # bucket in active use) gets the same self-healing coverage.
        bucket_names = [
            row[0] for row in
            db.query(MediaItem.bucket_name)
            .filter(MediaItem.b2_account_id == b2_acc.id)
            .distinct()
            .all()
            if row[0]
        ]

        total_missing = 0
        total_processed = 0

        for bucket_name in bucket_names:
            db_files = set(
                fn for (fn,) in
                db.query(MediaItem.file_name)
                .filter(MediaItem.b2_account_id == b2_acc.id, MediaItem.bucket_name == bucket_name)
                .all()
            )

            thumb_bucket_name = f"{bucket_name}-thumbs"
            thumb_files = set()
            try:
                thumb_bucket = client.b2_api.get_bucket_by_name(thumb_bucket_name)
                for file_version, _ in thumb_bucket.ls('', latest_only=True, recursive=True):
                    if file_version.action == 'upload':
                        thumb_files.add(file_version.file_name)
            except Exception as e:
                logger.error(f"Error reading thumb bucket {thumb_bucket_name}: {e}")
                continue

            missing = list(db_files - thumb_files)
            if not missing:
                continue

            logger.info(f"{bucket_name}: {len(missing)} hianyzo thumbnail talalva, potlas indul...")
            total_missing += len(missing)

            if max_test_items:
                missing = missing[:max_test_items]

            source_bucket = client.b2_api.get_bucket_by_name(bucket_name)

            for file_name in missing:
                if not ignore_time:
                    current_time = datetime.now().time()
                    if not (start_time <= current_time <= end_time):
                        logger.info(f"Time boundary reached ({current_time}), stopping thumbnail self-heal.")
                        return total_processed
                try:
                    _generate_and_upload_thumbnail(client, source_bucket, thumb_bucket_name, file_name)
                    total_processed += 1
                    logger.info(f"[{bucket_name}] Potolt thumbnail {total_processed}/{total_missing}: {file_name}")
                except Exception as e:
                    logger.error(f"Failed to generate thumbnail for {bucket_name}/{file_name}: {e}")

        logger.info(f"Thumbnail self-heal kesz. Potolva: {total_processed}/{total_missing}")
        return total_processed
    finally:
        db.close()
