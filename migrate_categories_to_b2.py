import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import DATABASE_URL
from backend.models import B2Account, MediaClassification, MediaItem
from backend.utils.b2_client import B2Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_categories():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        b2_account = db.query(B2Account).filter(B2Account.is_active == True).first()
        if not b2_account:
            logger.error("Nincs aktív B2 fiók!")
            return

        client = B2Client(b2_account.key_id, b2_account.application_key)
        
        # Olyan képeket keresünk, amelyeknek van kategóriájuk és nincsenek törölve
        classifications = db.query(MediaClassification).filter(
            MediaClassification.category != None,
            MediaClassification.is_deleted == False
        ).all()

        logger.info(f"Összesen {len(classifications)} kategorizált kép található az adatbázisban.")
        
        count = 0
        for cls in classifications:
            item = db.query(MediaItem).filter(MediaItem.file_name == cls.file_name).first()
            if not item:
                logger.warning(f"Nem található MediaItem a(z) {cls.file_name} fájlhoz.")
                continue
                
            bucket_name = item.bucket_name
            file_name = cls.file_name
            category = cls.category
            
            logger.info(f"[{count+1}/{len(classifications)}] Kategória ({category}) rögzítése B2 metaadatként: {file_name}")
            try:
                # Keresd meg a vödröt
                bucket = client.b2_api.get_bucket_by_name(bucket_name)
                # Keresd meg a fájlt
                file_version = bucket.get_file_info_by_name(file_name)
                
                # Vizsgáljuk meg, hogy van-e már category metaadata
                existing_info = file_version.file_info
                if existing_info.get('category') == category:
                    logger.info(f" -> Már be van állítva a '{category}' metaadat a B2-n, kihagyás.")
                    count += 1
                    continue
                
                file_info = dict(existing_info)
                file_info['category'] = category
                
                # "Másolás" önmagára az új file_info-val
                bucket.copy(
                    file_id=file_version.id_,
                    new_file_name=file_name,
                    file_info=file_info,
                    metadata_directive='REPLACE'
                )
                
                # Régi verzió törlése (opcionális, de ajánlott ha nem akarunk sok verziót tartani)
                bucket.delete_file_version(file_version.id_, file_name)
                
                logger.info(f" -> Metaadat sikeresen frissítve B2-n.")
            except Exception as e:
                logger.error(f" -> Hiba a {file_name} frissítésekor: {e}")
            
            count += 1
            
        logger.info("Migráció befejeződött!")
            
    except Exception as e:
        logger.exception(f"Kritikus hiba a migráció során: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("Ez a script végigmegy az összes lokálisan kategorizált képen, és felmásolja a kategória metaadatot a B2 felhőbe. Szeretnéd folytatni? (i/n): ")
    if confirm.lower() == 'i':
        migrate_categories()
    else:
        print("Megszakítva.")
