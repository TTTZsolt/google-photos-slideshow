#!/data/data/com.termux/files/usr/bin/bash
# Kikapcsolja az automatikus fenykep-feltoltest (a figyelo folyamat tovabb
# fut a hatterben, csak nem tolt fel semmit, amig ujra be nem kapcsolod).
rm -f "$HOME/.lumina_auto_upload_enabled"
echo "Automatikus fenykep-feltoltes KIKAPCSOLVA."
