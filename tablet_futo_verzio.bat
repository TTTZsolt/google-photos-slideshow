@echo off
echo --- Tablet: Aktiv verzio es allapot lekerdezese ---
echo Csatlakozas a tablethez (192.168.1.157)...

where ssh >nul 2>nul
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && echo '--- Aktiv Branch ---' && git rev-parse --abbrev-ref HEAD && echo && echo '--- Utolso Commit ---' && git log -1 --oneline && echo && echo '--- Mellekelt Backend Verzio (main.py) ---' && grep 'title=' backend/main.py"
) else (
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && echo '--- Aktiv Branch ---' && git rev-parse --abbrev-ref HEAD && echo && echo '--- Utolso Commit ---' && git log -1 --oneline && echo && echo '--- Mellekelt Backend Verzio (main.py) ---' && grep 'title=' backend/main.py"
)

echo.
pause
