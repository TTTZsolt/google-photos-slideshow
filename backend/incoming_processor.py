"""
incoming_processor.py - a 'beerkezo' B2 vodor idoszakos feldolgozasa.

Ez a vodor egy nyers "postalada": barmilyen kulso eszkoz (pl. a telefonon
futo FolderSync app, S3-kompatibilis modon) ide szinkronizalhat kepeket,
eredeti fajlnevvel, minden feldolgozas nelkul. Ez a modul rendszeresen
(l. main.py inditasi hook) atnezi ezt a vodrot, es minden talalt kepet:

  1. SHA1 alapjan ellenoriz (mar fent van-e a kepek02-ben, vagy korabban
     szandekosan torolve lett-e - tombstone), hogy elkerulje a duplikaciot
     es a szandekosan torolt tartalom veletlen "feltamasztasat".
  2. EXIF DateTimeOriginal alapjan kiszamolja az Ev/Honap celutvonalat
     (mappazasi_algoritmus_specifikacio.md szerint, album nelkuli ag).
  3. Nevet tisztitja, HEIC eseten JPG-re konvertal, 400px thumbnailt general.
  4. Feltolti a kepek02(-thumbs) vodrokbe, letrehozza az adatbazis-rekordokat.
  5. Torli az eredetit a beerkezo vodorbol.

Igy a telefon oldalan barmilyen kesz, S3-kompatibilis szinkron-app hasznalhato
(nem kell egyedi Termux-szkript) - az osszes "okos" feldolgozas itt, a
szerveren tortenik.
"""

import os
import re
import logging
import hashlib
import unicodedata
from io import BytesIO
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import B2Account, MediaItem, MediaClassification, DeletedContentHash
from .utils.b2_client import B2Client

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
THUMB_SIZE = (400, 400)


def clean_string(text: str) -> str:
    """Azonos a prepare_photos.py / takeout_to_b2_feltoltes.py clean_string()-jevel."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def get_exif_date(image_bytes: bytes):
    try:
        img = Image.open(BytesIO(image_bytes))
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if TAGS.get(tag, tag) == "DateTimeOriginal":
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass
    return None


def to_jpeg_bytes(pil_img: Image.Image, quality: int = 95) -> bytes:
    out = BytesIO()
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(out, "JPEG", quality=quality)
    return out.getvalue()


def create_thumbnail_bytes(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    if hasattr(img, "_getexif"):
        exif = img._getexif()
        if exif:
            orientation = exif.get(0x0112)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
    out = BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(out, "JPEG", quality=75, optimize=True)
    return out.getvalue()


def mark_as_processed_in_incoming(client: B2Client, bucket_name: str, file_name: str, file_id: str):
    """A beerkezo-beli eredetit 0 bajtos helyjelolore cimezi (nem torli teljesen
    a nevet) - igy a telefon-oldali szinkron-app (meretellenorzes nelkul
    beallitva) a nevet latva 'mar szinkronizalt'-nak tekinti, es nem tolti
    fel ujra vegtelenul ugyanazt a fajlt minden szinkronnal. Csak nevenkent
    egyszer fut le (torles + ures ujrafeltoltes), utana a nev mindig letezik,
    0 bajttal - elhanyagolhato tarhelykoltseg."""
    try:
        client.delete_file_version(bucket_name, file_name, file_id)
    except Exception as e:
        logger.warning(f"Incoming: nem sikerult torolni az eredetit ({file_name}): {e}")
    try:
        client.upload_byte_stream(bucket_name, file_name, b"", content_type="application/octet-stream")
    except Exception as e:
        logger.warning(f"Incoming: nem sikerult 0 bajtos helyjelolot feltolteni ({file_name}): {e}")


def compute_target_path(dt: datetime, filename: str) -> str:
    """A specifikacio "nincs album" aga: {ev}/{honap}/{tisztitott nev}{kiterjesztes}."""
    name, ext = os.path.splitext(filename)
    clean_name = clean_string(name)
    ext = ext.lower()
    if ext in (".heic", ".heif"):
        ext = ".jpg"
    return f"{dt.year:04d}/{dt.month:02d}/{clean_name}{ext}"


def process_incoming_bucket() -> dict:
    """Egyszeri, teljes korű atvizsgalasa a beerkezo vodornek. Blokkolo
    (szinkron) fuggveny - hivasnal hasznalj hozza kulon szalat/thread-et,
    ha async kontextusbol hivod (l. main.py)."""
    db: Session = SessionLocal()
    processed = 0
    skipped = 0
    failed = 0
    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account or not b2_account.incoming_bucket_name:
            return {"processed": 0, "skipped": 0, "failed": 0, "message": "Nincs beerkezo vodor beallitva."}

        client = B2Client(b2_account.key_id, b2_account.application_key)
        incoming_bucket = b2_account.incoming_bucket_name
        target_bucket = b2_account.bucket_name

        files = list(client.list_files(incoming_bucket))
        if not files:
            return {"processed": 0, "skipped": 0, "failed": 0, "message": "Nincs uj fajl."}

        logger.info(f"Incoming feldolgozas: {len(files)} fajl talalva a '{incoming_bucket}' vodorben.")

        for file_version in files:
            file_name = file_version.file_name
            ext = os.path.splitext(file_name)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                logger.warning(f"Incoming: nem tamogatott kiterjesztes, kihagyva: {file_name}")
                continue

            if file_version.size == 0:
                # Sajat 0 bajtos helyjelolonk (l. mark_as_processed_in_incoming) -
                # mar korabban feldolgoztuk, csendben atugorjuk.
                continue

            try:
                data = client.download_bytes(incoming_bucket, file_name)
            except Exception as e:
                logger.error(f"Incoming: letoltesi hiba ({file_name}): {e}")
                failed += 1
                continue

            sha1 = hashlib.sha1(data).hexdigest()

            already_exists = db.query(MediaItem).filter(
                MediaItem.bucket_name == target_bucket,
                MediaItem.sha1 == sha1
            ).first() is not None
            already_deleted = db.query(DeletedContentHash).filter(
                DeletedContentHash.sha1 == sha1
            ).first() is not None

            if already_exists or already_deleted:
                reason = "mar-fent-van" if already_exists else "szandekosan-torolve"
                logger.info(f"Incoming: kihagyva ({reason}): {file_name}")
                mark_as_processed_in_incoming(client, incoming_bucket, file_name, file_version.id_)
                skipped += 1
                continue

            exif_date = get_exif_date(data)
            effective_date = exif_date or datetime.fromtimestamp(file_version.upload_timestamp / 1000)
            target_path = compute_target_path(effective_date, file_name)

            upload_bytes = data
            if ext in (".heic", ".heif"):
                try:
                    img = Image.open(BytesIO(data))
                    upload_bytes = to_jpeg_bytes(img)
                except Exception as e:
                    logger.error(f"Incoming: HEIC konverzio hiba ({file_name}): {e}")
                    failed += 1
                    continue

            try:
                thumb_bytes = create_thumbnail_bytes(data)
            except Exception as e:
                logger.warning(f"Incoming: thumbnail hiba ({file_name}): {e}")
                thumb_bytes = None

            try:
                new_version = client.upload_byte_stream(
                    target_bucket, target_path, upload_bytes, content_type="image/jpeg"
                )
                if thumb_bytes:
                    client.upload_byte_stream(
                        f"{target_bucket}-thumbs", target_path, thumb_bytes, content_type="image/jpeg"
                    )
            except Exception as e:
                logger.error(f"Incoming: feltoltesi hiba ({file_name} -> {target_path}): {e}")
                failed += 1
                continue

            media_item = MediaItem(
                id=new_version.id_,
                b2_account_id=b2_account.id,
                bucket_name=target_bucket,
                file_name=target_path,
                mime_type="image/jpeg",
                size=len(upload_bytes),
                creation_time=effective_date,
                sha1=getattr(new_version, "content_sha1", sha1),
                is_in_sorter=False,
            )
            db.merge(media_item)

            existing_mc = db.query(MediaClassification).filter(
                MediaClassification.file_name == target_path
            ).first()
            if not existing_mc:
                db.add(MediaClassification(file_name=target_path, category=None, is_deleted=False))

            db.commit()

            mark_as_processed_in_incoming(client, incoming_bucket, file_name, file_version.id_)

            logger.info(f"Incoming: feldolgozva {file_name} -> {target_bucket}/{target_path}")
            processed += 1

        return {"processed": processed, "skipped": skipped, "failed": failed}
    except Exception as e:
        logger.exception(f"process_incoming_bucket hiba: {e}")
        return {"processed": processed, "skipped": skipped, "failed": failed, "error": str(e)}
    finally:
        db.close()
