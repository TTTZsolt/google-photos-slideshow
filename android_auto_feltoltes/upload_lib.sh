#!/data/data/com.termux/files/usr/bin/bash
#
# upload_lib.sh - kozos feltoltesi logika, amit tobb script is hasznal
# (lumina_watcher.sh - automatikus figyeles, manual_upload.sh - a
# LuminaFeltoltes mappa utolagos "flush"-elese). Ne futtasd onmagaban, csak
# source-old be:
#   source "$HOME/lumina_auto_feltoltes/upload_lib.sh"

CAMERA_DIR="$HOME/storage/dcim/Camera"
LOG_FILE="$HOME/lumina_auto_upload.log"
REMOTE_MAIN="b2_storage:Kepek02"
REMOTE_THUMB="b2_storage:kepek02-thumbs"
THUMB_SIZE="400x400"

# Kezi, kivalasztasos feltoltes mappaja: a Galeria/Fotok app natic tobbes
# kijelolesevel ide "Mentve"/"Masolva" kepek automatikusan feltoltodnek,
# fuggetlenul attol, be van-e kapcsolva az automatikus feltoltes (a
# felhasznalo mar explicit dontott, amikor idehelyezte a fajlt). Sikeres
# feltoltes utan a fajl TORLODIK a telefonrol (mar biztonsagban van a B2-n,
# nem kell duplan foglalnia a helyet), es csak egy sor kerul a
# $STAGING_ARCHIVE_LOG naplofajlba (fajlnev + idopont) - nem maga a kep.
STAGING_DIR="$HOME/storage/shared/Pictures/LuminaFeltoltes"
STAGING_ARCHIVE="$STAGING_DIR/feltoltve"
STAGING_ARCHIVE_LOG="$STAGING_ARCHIVE/feltoltott_kepek.csv"

# A mindig futo (tablet) Lumina-peldany, aminek szolnunk kell feltoltes utan,
# hogy azonnal felvegye az uj kepet az adatbazisaba (kulonben csak fizikailag
# van fent a B2-n, a Lumina feluleten meg nem latszik, amig valaki kezzel nem
# szinkronizal). A PC-s fejlesztoi peldanyt szandekosan nem erinti.
LUMINA_SERVER="100.67.27.6:8000"
B2_ACCOUNT_ID="1"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

trigger_lumina_sync() {
    if curl -s -m 15 -X POST "http://${LUMINA_SERVER}/b2/sync/${B2_ACCOUNT_ID}" >>"$LOG_FILE" 2>&1; then
        log "OK (sync): a Lumina ertesitve, adatbazis-szinkron elindult"
    else
        log "FIGYELEM: nem sikerult ertesiteni a Luminat (${LUMINA_SERVER}) - a kep fent van a B2-n, de kesobb kezi Sync kellhet"
    fi
}

clean_string() {
    # Ugyanaz a logika, mint a Python clean_string()-ben: ekezetek le,
    # kisbetu, minden nem a-z0-9. karakter kotojelre, kotojel-osszevonas.
    echo -n "$1" \
        | iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9.]/-/g; s/-+/-/g; s/^-+//; s/-+$//'
}

upload_photo() {
    local filepath="$1"
    local filename
    filename=$(basename "$filepath")
    local lower_name
    lower_name=$(echo "$filename" | tr '[:upper:]' '[:lower:]')

    case "$lower_name" in
        *.jpg|*.jpeg|*.png|*.heic|*.heif) ;;
        *) return 1 ;;
    esac

    if [ ! -f "$filepath" ]; then
        return 1  # a fajl kozben torlodott/atnevezodott
    fi

    # Varjunk, amig a fenykepezogep app befejezi az iras/mentest
    # (meret-stabilitas ellenorzese ket mintavetel kozott).
    local size1 size2
    size1=$(stat -c%s "$filepath" 2>/dev/null)
    sleep 2
    size2=$(stat -c%s "$filepath" 2>/dev/null)
    if [ -z "$size1" ] || [ "$size1" != "$size2" ]; then
        sleep 3
    fi
    if [ ! -f "$filepath" ]; then
        return 1
    fi

    # EXIF datum (Ev/Honap), tartalek: fajl modositasi ideje
    local year_month
    year_month=$(exiftool -DateTimeOriginal -d "%Y/%m" -s3 "$filepath" 2>/dev/null)
    if [ -z "$year_month" ]; then
        year_month=$(date -r "$filepath" '+%Y/%m')
    fi

    local base_name="${filename%.*}"
    local ext="${filename##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    if [ "$ext" = "heic" ] || [ "$ext" = "heif" ]; then
        ext="jpg"
    fi

    local clean_name
    clean_name=$(clean_string "$base_name")
    local target_path="${year_month}/${clean_name}.${ext}"

    # Ha kell, JPG-re konvertaljuk (HEIC eseten), es legyartjuk a thumbnailt
    local upload_source="$filepath"
    local tmp_converted=""
    if [ "$ext" = "jpg" ] && [ "$(echo "${filename##*.}" | tr '[:upper:]' '[:lower:]')" != "jpg" ] && [ "$(echo "${filename##*.}" | tr '[:upper:]' '[:lower:]')" != "jpeg" ]; then
        tmp_converted="$HOME/.lumina_tmp_$$_converted.jpg"
        if convert "$filepath" "$tmp_converted" 2>>"$LOG_FILE"; then
            upload_source="$tmp_converted"
        else
            log "HIBA: HEIC->JPG konverzio sikertelen ($filepath)"
            return 1
        fi
    fi

    # SHA1-ellenorzes feltoltes elott - ugyanaz a vedelem, mint a Takeout
    # feltoltonel: ne toltsuk fel ujra, ami mar fent van, es soha ne
    # hozzuk vissza, amit tudatosan toroltunk (tombstone).
    local file_sha1
    file_sha1=$(sha1sum "$upload_source" 2>/dev/null | cut -d' ' -f1)
    if [ -n "$file_sha1" ]; then
        local check_response already_exists already_deleted
        check_response=$(curl -s -m 15 "http://${LUMINA_SERVER}/api/media/check-sha1/${file_sha1}" 2>>"$LOG_FILE")
        already_exists=$(echo "$check_response" | jq -r '.exists // false' 2>/dev/null)
        already_deleted=$(echo "$check_response" | jq -r '.deleted // false' 2>/dev/null)

        if [ "$already_deleted" = "true" ]; then
            log "KIHAGYVA (tudatosan torolt tartalom, nem allitjuk vissza): $filepath"
            [ -n "$tmp_converted" ] && rm -f "$tmp_converted"
            return 0
        fi
        if [ "$already_exists" = "true" ]; then
            log "KIHAGYVA (tartalom mar fent van a B2-n): $filepath"
            [ -n "$tmp_converted" ] && rm -f "$tmp_converted"
            return 0
        fi
    fi

    local tmp_thumb="$HOME/.lumina_tmp_$$_thumb.jpg"
    if ! convert "$upload_source" -resize "$THUMB_SIZE" -quality 75 "$tmp_thumb" 2>>"$LOG_FILE"; then
        log "FIGYELEM: thumbnail generalas sikertelen ($filepath), csak az eredetit toltom fel"
        tmp_thumb=""
    fi

    local upload_result=1
    if rclone copyto "$upload_source" "${REMOTE_MAIN}/${target_path}" 2>>"$LOG_FILE"; then
        log "OK (eredeti): $filepath -> ${REMOTE_MAIN}/${target_path}"
        upload_result=0
        if [ -n "$tmp_thumb" ] && [ -f "$tmp_thumb" ]; then
            if rclone copyto "$tmp_thumb" "${REMOTE_THUMB}/${target_path}" 2>>"$LOG_FILE"; then
                log "OK (thumb): ${REMOTE_THUMB}/${target_path}"
            else
                log "HIBA: thumbnail feltoltese sikertelen (${target_path})"
            fi
        fi
        trigger_lumina_sync
    else
        log "HIBA: feltoltes sikertelen ($filepath)"
    fi

    [ -n "$tmp_converted" ] && rm -f "$tmp_converted"
    [ -n "$tmp_thumb" ] && rm -f "$tmp_thumb"

    return "$upload_result"
}

upload_and_archive_staging() {
    # A STAGING_DIR-be kezzel (Galeria-megosztassal) betett kep feltoltese.
    # Sikeres feltoltes utan a fajl TORLODIK a telefonrol (mar fent van a
    # B2-n), es csak egy sor kerul a STAGING_ARCHIVE_LOG naplofajlba
    # (fajlnev + idopont) - igy nem foglal duplan helyet a telefonon, de
    # megmarad a nyoma, hogy mi es mikor lett feltoltve. Sikertelen
    # feltoltes eseten a fajl a helyen marad, legkozelebb ujra probalkozunk.
    local filepath="$1"
    local filename
    filename=$(basename "$filepath")

    mkdir -p "$STAGING_ARCHIVE"
    if upload_photo "$filepath"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'),${filename}" >> "$STAGING_ARCHIVE_LOG"
        rm -f "$filepath"
    fi
}

process_staging_folder_now() {
    # Utolagos/kezi "flush": minden, a STAGING_DIR-ben (nem az archivumban)
    # jelenleg talalhato kepet feltolt. Arra az esetre, ha a figyelo folyamat
    # nem futott epp akkor, amikor a fajlt odatetted.
    mkdir -p "$STAGING_DIR" "$STAGING_ARCHIVE"
    find "$STAGING_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' -o -iname '*.heif' \) -print0 | \
    while IFS= read -r -d '' filepath; do
        upload_and_archive_staging "$filepath"
    done
}
