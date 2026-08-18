#!/data/data/com.termux/files/usr/bin/bash
# Ezt a fajlt a ~/.termux/boot/ mappaba kell masolni (Termux:Boot app kell
# hozza, l. user_guide.md). Telefon-ujrainditas utan automatikusan elinditja
# a figyelo folyamatot a hatterben - a tenyleges feltoltes csak akkor aktiv,
# ha a start_auto_feltoltes.sh mar bekapcsolta (a kapcsolo-fajl allapota
# tuleli az ujrainditast).
termux-wake-lock
cd "$HOME/lumina_auto_feltoltes" || exit 1
nohup bash lumina_watcher.sh >> "$HOME/lumina_auto_upload.log" 2>&1 &
