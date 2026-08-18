#!/data/data/com.termux/files/usr/bin/bash
#
# manual_upload.sh - "utolagos flush": feltolti mindazt, ami jelenleg a
# STAGING_DIR mappaban van (l. upload_lib.sh), es meg nem lett feldolgozva.
#
# A tenyleges kivalasztas mar a telefon Galeria/Fotok appjaban tortenik
# (natic bengekep-racs, tobbes kijeloles) - onnan "Mentes"/"Masolas ide"
# muvelettel a STAGING_DIR mappaba kell tenni a kepeket, amiket fel
# szeretnel tolteni. A hattérben futo lumina_watcher.sh ezt a mappat is
# folyamatosan figyeli es magatol feltolti - ezt a scriptet csak akkor kell
# kezzel futtatni, ha a figyelo epp nem futott, amikor odatetted a kepeket.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/upload_lib.sh"

before_count=$(find "$STAGING_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' -o -iname '*.heif' \) 2>/dev/null | wc -l)

if [ "$before_count" -eq 0 ]; then
    termux-toast "Nincs feltoltendo kep a LuminaFeltoltes mappaban." 2>/dev/null
    echo "Nincs feltoltendo kep a $STAGING_DIR mappaban."
    exit 0
fi

process_staging_folder_now

termux-toast "Kesz: $before_count kep feltoltve." 2>/dev/null
echo "Kesz: $before_count kep feltoltve (l. $LOG_FILE)."
