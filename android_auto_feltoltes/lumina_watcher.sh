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
# A tenyleges feltoltesi logikat (EXIF-datum, nevtisztitas, rclone, stb.) az
# upload_lib.sh tartalmazza - ezt hasznalja a manual_upload.sh (kezi,
# kivalasztasos feltoltes) is, hogy ne legyen ket helyen karbantartando kod.
#
# Fuggosegek (egyszeri telepites Termux-ban):
#   pkg install inotify-tools rclone exiftool imagemagick coreutils
#   rclone config   (allitsd be a "b2_storage" remote-ot a B2-hez, ugyanugy,
#                     mint a PC-n hasznalt Fenykep elokeszites projektben)
#   termux-setup-storage   (hogy a ~/storage/dcim/Camera elerheto legyen)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/upload_lib.sh"

TOGGLE_FLAG="$HOME/.lumina_auto_upload_enabled"

log "--- Lumina auto-feltolto figyelo elindult ($CAMERA_DIR) ---"

inotifywait -m -e close_write -e moved_to --format '%w%f' "$CAMERA_DIR" 2>>"$LOG_FILE" | \
while read -r filepath; do
    if [ ! -f "$TOGGLE_FLAG" ]; then
        continue
    fi
    upload_photo "$filepath"
done
