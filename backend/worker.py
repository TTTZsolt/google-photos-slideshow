import logging
from sqlalchemy.orm import Session
from sqlalchemy import delete, func
from .database import SessionLocal
from .models import MediaItem, B2Account, MediaClassification
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Backblaze B2 Sync Worker

def sync_b2_worker(b2_account_id: int, target_bucket: str = None):
    db = SessionLocal()
    try:
        from .utils.b2_client import B2Client
        
        b2_account = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
        if not b2_account:
            logger.error(f"B2 Account {b2_account_id} not found")
            return

        # If target_bucket is not specified, sync main, source and trash
        buckets_to_sync = []
        unique_buckets = set()
        
        if target_bucket:
            unique_buckets.add(target_bucket)
        else:
            if b2_account.bucket_name:
                unique_buckets.add(b2_account.bucket_name)
            if b2_account.source_bucket_name:
                unique_buckets.add(b2_account.source_bucket_name)
            if b2_account.trash_bucket_name:
                unique_buckets.add(b2_account.trash_bucket_name)
        
        buckets_to_sync = list(unique_buckets)

        logger.info(f"Starting B2 sync for account {b2_account_id}, buckets: {buckets_to_sync}")
        b2_account.sync_status = "Syncing"
        b2_account.sync_count = 0
        db.commit()

        client = B2Client(b2_account.key_id, b2_account.application_key)
        
        # V14.1 Improvement: Pre-calculate total files for progress bar
        logger.info(f"Pre-calculating total file count for account {b2_account_id}...")
        total_expected = 0
        all_bucket_files = {} # bucket_name -> [file_versions]
        
        for bucket_name in buckets_to_sync:
            logger.info(f"Listing files in {bucket_name} for count...")
            files = list(client.list_files(bucket_name))
            all_bucket_files[bucket_name] = files
            total_expected += len(files)
        
        b2_account.sync_total = total_expected
        b2_account.sync_count = 0
        db.commit()
        logger.info(f"Total files to process: {total_expected}")

        total_count = 0
        for bucket_name, file_versions in all_bucket_files.items():
            logger.info(f"Syncing bucket: {bucket_name} ({len(file_versions)} files)")
            is_trash_bucket = (bucket_name == b2_account.trash_bucket_name)

            # Robusztussag B2 "eshetoleges konzisztencia" ellen: a fenti
            # listazas kozvetlenul sok/gyors B2-muvelet utan atmenetileg
            # KEVESEBB fajlt adhat vissza, mint amennyi valojaban ott van.
            # A regi kod ilyenkor vakon torolte a "hianyzo" fajlok DB-sorat
            # (a torles-statusszal egyutt, ha eppen a Lomtarrol volt szo) -
            # 2026-09-01-en pontosan ez tortent: egy resync a Lomtarban
            # 24 valodi elembol csak 3-at latott, es a maradek 24
            # media_items/media_classifications sora elveszett, holott a
            # fajlok tenylegesen megvoltak a B2-n. Ezert most, mielott
            # barmit is torolnenk, fajlonkent celzottan megerositjuk a
            # hianyt egy kulon, direkt lekerdezessel.
            fresh_by_name = {fv.file_name: fv for fv in file_versions}
            existing_rows = {
                fn: item_id for fn, item_id in
                db.query(MediaItem.file_name, MediaItem.id)
                .filter(MediaItem.b2_account_id == b2_account_id, MediaItem.bucket_name == bucket_name)
                .all()
            }
            missing_from_listing = set(existing_rows) - set(fresh_by_name)

            confirmed_removed_names = set()
            if missing_from_listing:
                logger.info(f"{bucket_name}: {len(missing_from_listing)} fajl hianyzik a friss listazasbol, egyenkenti megerositas...")
                try:
                    check_bucket = client.b2_api.get_bucket_by_name(bucket_name)
                except Exception as e:
                    logger.error(f"Nem sikerult megnyitni a {bucket_name} vodort a megerositeshez: {e}")
                    check_bucket = None

                for fname in missing_from_listing:
                    still_there = False
                    if check_bucket:
                        try:
                            check_bucket.get_file_info_by_name(fname)
                            still_there = True
                        except Exception:
                            still_there = False
                    if still_there:
                        logger.warning(f"{bucket_name}/{fname}: a bulk-listazas kihagyta, de valojaban meg mindig ott van - MEGTARTVA (nem torolve).")
                    else:
                        confirmed_removed_names.add(fname)

            # Csak a megerositetten eltunt fajlok soranak torlese, plusz
            # azoke, amik ugyan megvannak, de uj B2-verziot (uj id-t)
            # kaptak - ezeket a lenti ciklus ujra beszurja a friss id-vel.
            ids_to_delete = [
                item_id for fn, item_id in existing_rows.items()
                if fn in confirmed_removed_names
                or (fn in fresh_by_name and fresh_by_name[fn].id_ != item_id)
            ]
            if ids_to_delete:
                db.execute(delete(MediaItem).where(MediaItem.id.in_(ids_to_delete)))
                db.commit()

            count = 0
            for file_version in file_versions:
                # Filter for images
                mime = file_version.content_type
                file_name = file_version.file_name
                
                # Check extension if mime type is generic or missing
                ext = file_name.lower().split('.')[-1]
                if mime and not mime.startswith('image/'):
                    if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                        # Even if skipped, we should count it as "processed" to keep percentage correct?
                        # Or better: total_expected should only include images.
                        # Let's subtract from total if skipped.
                        total_expected -= 1
                        continue
                
                media_item = MediaItem(
                    id=file_version.id_,
                    b2_account_id=b2_account_id,
                    bucket_name=bucket_name,
                    file_name=file_name,
                    mime_type=mime if (mime and mime.startswith('image/')) else f"image/{ext}",
                    size=file_version.size,
                    creation_time=datetime.fromtimestamp(file_version.upload_timestamp / 1000),
                    sha1=getattr(file_version, "content_sha1", None)
                )
                db.merge(media_item)

                # Process file_info metadata for category
                category = file_version.file_info.get('category') if file_version.file_info else None
                
                # Sync classification
                class_item = db.query(MediaClassification).filter(MediaClassification.file_name == file_name).first()
                if not class_item:
                    class_item = MediaClassification(
                        file_name=file_name, 
                        category=category, 
                        is_deleted=is_trash_bucket
                    )
                    db.add(class_item)
                else:
                    # Update existing record
                    if category:
                        class_item.category = category
                    
                    class_item.is_deleted = is_trash_bucket
                    if not is_trash_bucket:
                        pass

                count += 1
                total_count += 1
                
                # Progress update every 100 items or at the end
                if total_count % 100 == 0 or total_count == b2_account.sync_total:
                    db.commit()
                    # Refresh object to update sync_count
                    b2_account = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
                    b2_account.sync_count = total_count
                    b2_account.sync_total = total_expected # Update in case it changed due to filter
                    db.commit()
                    logger.info(f"Indexed {total_count}/{total_expected} files...")
            
        b2_account = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
        b2_account.last_synced_at = func.now()
        b2_account.sync_status = "Finished"
        b2_account.sync_count = total_count
        b2_account.sync_total = total_expected
        db.commit()

        # V14.3.1 Cleanup: Remove classification records that no longer exist in ANY B2 bucket
        logger.info("Cleaning up orphaned classification records...")
        # Get all unique file names currently in MediaItem
        subquery = db.query(MediaItem.file_name)
        # Delete from MediaClassification where file_name is NOT in the list of existing files
        orphaned_count = db.query(MediaClassification).filter(~MediaClassification.file_name.in_(subquery)).delete(synchronize_session=False)
        db.commit()
        
        logger.info(f"Finished sync for account {b2_account_id}. Total items: {total_count}, Cleaned up: {orphaned_count} orphans.")

        # Onjavito thumbnail-potlas: ha egy korabbi mozgatas/uj feltoltes
        # kozben a thumbnail resze elhasalt (halozati hiba, B2 throttling),
        # minden resync ezt automatikusan eszreveszi es potolja - igy egy
        # kep sosem marad tartosan "fekete" a feluleten.
        try:
            from .thumb_worker import generate_missing_thumbnails
            generate_missing_thumbnails(b2_account_id=b2_account_id, ignore_time=True)
        except Exception as heal_err:
            logger.error(f"Thumbnail self-heal step failed: {heal_err}")

    except Exception as e:
        logger.exception(f"Error syncing B2 account {b2_account_id}: {e}")
        b2_account = db.query(B2Account).filter(B2Account.id == b2_account_id).first()
        if b2_account:
            b2_account.sync_status = f"Error: {str(e)[:50]}"
            db.commit()
    finally:
        db.close()

def sync_all_accounts_worker():
    db = SessionLocal()
    try:
        # Syncing B2 accounts
        b2_accounts = db.query(B2Account).filter(B2Account.is_active == True).all()
        for b2_acc in b2_accounts:
            sync_b2_worker(b2_acc.id)
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_accounts_worker()
