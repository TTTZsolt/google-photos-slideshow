@echo off
echo --- Frissites: Slideshow Szerver a Tableten ---
echo Pulling latest changes from GitHub...

:: Megprobaljuk a rendszer SSH-t
where ssh >nul 2>nul
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git pull origin main"
) else (
    echo A rendszer SSH nem talalhato, probalom a Git mappabol...
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git pull origin main"
)

echo.
echo A frissites (git pull) befejezodott.
echo.
echo Az aktualis verzio a Tableten:
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git log -1 --oneline"
) else (
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git log -1 --oneline"
)
echo.
echo Most mar elindithatod a szervert a start_tablet.bat-tal!
pause
