@echo off
echo --- Leallitas: Slideshow Szerver a Tableten ---

:: Folyamat leállítása
where ssh >nul 2>nul
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "catt stop && (pkill -f 'python -m backend.main' || kill $(pgrep -f 'python -m backend.main'))"
) else (
    echo A rendszer SSH nem talalhato, probalom a Git mappabol...
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "catt stop && (pkill -f 'python -m backend.main' || kill $(pgrep -f 'python -m backend.main'))"
)

echo.
echo Leallitasi parancs elkuldve.
pause
