#!/data/data/com.termux/files/usr/bin/bash
#
# manual_upload.sh - kezi, kivalasztasos feltoltes: megjeleniti a kamera-mappa
# legutobbi kepeit egy tobbes-kijeloleses (checkbox) parbeszedablakban, es a
# kijelolt kepeket feltolti a Lumina Kepek02 vodorbe - ugyanazzal a logikaval,
# mint az automatikus figyelo (lumina_watcher.sh).
#
# Hasznos, ha az automatikus feltoltes ki volt kapcsolva, amikor a kep
# keszult, es utolag akarod felkuldeni.
#
# Fuggosegek (az alap csomagokon felul):
#   pkg install termux-api jq
#   + a Termux:API companion app telepitve (F-Droid, UGYANARROL a forrasrol,
#     mint a fo Termux app, kulonben nem lathatja a Termux a parbeszedablak
#     eredmenyet - l. a Termux:Widget-nel tapasztalt hasonlo problemat)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/upload_lib.sh"

MAX_LIST=50

# Legutobbi kepek, legujabb elol - a dialogus kezelhetetlen lenne, ha a
# teljes kamera-elozmenyt felsorolnank, ezert csak az utolso MAX_LIST db-ot
# ajanljuk fel.
mapfile -t recent_files < <(ls -t "$CAMERA_DIR" 2>/dev/null | grep -Ei '\.(jpg|jpeg|png|heic|heif)$' | head -n "$MAX_LIST")

if [ "${#recent_files[@]}" -eq 0 ]; then
    termux-toast "Nincs kep a kamera-mappaban." 2>/dev/null
    echo "Nincs kep a kamera-mappaban."
    exit 0
fi

# Vesszovel elvalasztott lista a dialogushoz
values=$(IFS=,; echo "${recent_files[*]}")

selection_json=$(termux-dialog checkbox -t "Feltoltendo kepek kivalasztasa" -v "$values")

selected=$(echo "$selection_json" | jq -r '.values[]?.text // empty')

if [ -z "$selected" ]; then
    termux-toast "Nem valasztottal ki kepet." 2>/dev/null
    echo "Nem lett kivalasztva kep, nincs teendo."
    exit 0
fi

count=0
while IFS= read -r fname; do
    [ -z "$fname" ] && continue
    upload_photo "${CAMERA_DIR}/${fname}"
    count=$((count + 1))
done <<< "$selected"

termux-toast "Kesz: $count kep feltoltve." 2>/dev/null
echo "Kesz: $count kep feltoltve (l. $LOG_FILE)."
