#!/data/data/com.termux/files/usr/bin/bash
#
# lumina_watcher.sh - folyamatosan figyeli a telefon kamera-mappajat, es
# minden uj kepet automatikusan feltolt a Lumina Kepek02 vodorbe (kozvetlenul,
# kategoria nelkul - a mappazasi_algoritmus_specifikacio.md szerinti
# Ev/Honap struktura, EXIF-datum alapjan).
#
# A feltoltes csak akkor tortenik, ha a $TOGGLE_FLAG fajl letezik - ezt a
# start_auto_feltoltes.sh / stop_auto_feltoltes.sh kapcsolja be/ki. Maga a
# figyelo folyamat (ez a script) a Termux:Boot-tal folyamatosan fut,
# fuggetlenul attol, be van-e kapcsolva a tenyleges feltoltes.
#
# Fuggosegek (egyszeri telepites Termux-ban):
#   pkg install inotify-tools rclone exiftool imagemagick coreutils
#   rclone config   (allitsd be a "b2_storage" remote-ot a B2-hez, ugyanugy,
#                     mint a PC-n hasznalt Fenykep elokeszites projektben)
#   termux-setup-storage   (hogy a ~/storage/dcim/Camera elerheto legyen)

CAMERA_DIR="$HOME/storage/dcim/Camera"
TOGGLE_FLAG="$HOME/.lumina_auto_upload_enabled"
LOG_FILE="$HOME/lumina_auto_upload.log"
REMOTE_MAIN="b2_storage:Kepek02"
REMOTE_THUMB="b2_storage:kepek02-thumbs"
THUMB_SIZE="400x400"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
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
        *) return ;;
    esac

    if [ ! -f "$filepath" ]; then
        return  # a fajl kozben torlodott/atnevezodott
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
        return
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
            return
        fi
    fi

    local tmp_thumb="$HOME/.lumina_tmp_$$_thumb.jpg"
    if ! convert "$upload_source" -resize "$THUMB_SIZE" -quality 75 "$tmp_thumb" 2>>"$LOG_FILE"; then
        log "FIGYELEM: thumbnail generalas sikertelen ($filepath), csak az eredetit toltom fel"
        tmp_thumb=""
    fi

    if rclone copyto "$upload_source" "${REMOTE_MAIN}/${target_path}" 2>>"$LOG_FILE"; then
        log "OK (eredeti): $filepath -> ${REMOTE_MAIN}/${target_path}"
        if [ -n "$tmp_thumb" ] && [ -f "$tmp_thumb" ]; then
            if rclone copyto "$tmp_thumb" "${REMOTE_THUMB}/${target_path}" 2>>"$LOG_FILE"; then
                log "OK (thumb): ${REMOTE_THUMB}/${target_path}"
            else
                log "HIBA: thumbnail feltoltese sikertelen (${target_path})"
            fi
        fi
    else
        log "HIBA: feltoltes sikertelen ($filepath)"
    fi

    [ -n "$tmp_converted" ] && rm -f "$tmp_converted"
    [ -n "$tmp_thumb" ] && rm -f "$tmp_thumb"
}

log "--- Lumina auto-feltolto figyelo elindult ($CAMERA_DIR) ---"

inotifywait -m -e close_write -e moved_to --format '%w%f' "$CAMERA_DIR" 2>>"$LOG_FILE" | \
while read -r filepath; do
    if [ ! -f "$TOGGLE_FLAG" ]; then
        continue
    fi
    upload_photo "$filepath"
done
