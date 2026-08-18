#!/data/data/com.termux/files/usr/bin/bash
# Megmutatja, be van-e kapcsolva a feltoltes, fut-e a figyelo folyamat,
# es az utolso par naplosort.
if [ -f "$HOME/.lumina_auto_upload_enabled" ]; then
    echo "Allapot: BEKAPCSOLVA"
else
    echo "Allapot: KIKAPCSOLVA"
fi

if pgrep -f "inotifywait.*Camera" > /dev/null; then
    echo "Figyelo folyamat: FUT"
else
    echo "Figyelo folyamat: NEM FUT (inditsd: bash lumina_watcher.sh &)"
fi

echo ""
echo "--- Utolso 10 naplosor ---"
tail -n 10 "$HOME/lumina_auto_upload.log" 2>/dev/null || echo "(meg nincs naplo)"
