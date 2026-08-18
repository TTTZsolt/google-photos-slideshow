#!/data/data/com.termux/files/usr/bin/bash
# Bekapcsolja az automatikus fenykep-feltoltest.
# A figyelo folyamatnak (lumina_watcher.sh) mar futnia kell a hatterben
# (a Termux:Boot inditja telefon-ujrainditaskor) - ez a script csak a
# "kapcsolot" allitja at.
touch "$HOME/.lumina_auto_upload_enabled"
echo "Automatikus fenykep-feltoltes BEKAPCSOLVA."
