@echo off
echo --- Tablet: Aktiv verzio es allapot lekerdezese ---
echo Csatlakozas a tablethez (192.168.1.157)...

where ssh >nul 2>nul
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && VERSION=$(grep 'title=' backend/main.py | grep -o 'V[0-9.]*') && echo '--- Lumina Allapot ---' && echo 'Verzio: '$VERSION && echo -n 'Leiras: ' && (grep \"\*\*$VERSION\*\*\" README.md | sed 's/.*: //' || echo 'Nincs leiras') && echo && echo '--- Git Info ---' && echo -n 'Branch: ' && git rev-parse --abbrev-ref HEAD && echo -n 'Commit: ' && git log -1 --oneline && echo && echo '--- Szerver Statusz ---' && (pgrep -f 'python -m backend.main' > /dev/null && echo 'A SZERVER FUT' || echo 'A SZERVER NEM FUT')"
) else (
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && VERSION=$(grep 'title=' backend/main.py | grep -o 'V[0-9.]*') && echo '--- Lumina Allapot ---' && echo 'Verzio: '$VERSION && echo -n 'Leiras: ' && (grep \"\*\*$VERSION\*\*\" README.md | sed 's/.*: //' || echo 'Nincs leiras') && echo && echo '--- Git Info ---' && echo -n 'Branch: ' && git rev-parse --abbrev-ref HEAD && echo -n 'Commit: ' && git log -1 --oneline && echo && echo '--- Szerver Statusz ---' && (pgrep -f 'python -m backend.main' > /dev/null && echo 'A SZERVER FUT' || echo 'A SZERVER NEM FUT')"
)

echo.
pause
