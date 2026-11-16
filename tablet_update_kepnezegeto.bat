@echo off
echo --- Frissites: Slideshow Szerver a Tableten ---
echo A tablet azt az agat frissiti, amelyiken eppen all (nem valt at a main-re).

:: Megprobaljuk a rendszer SSH-t, kulonben a Git mappabolit
set "SSH=ssh"
where ssh >nul 2>nul
if %errorlevel% neq 0 set "SSH=C:\Program Files\Git\usr\bin\ssh.exe"

echo [1/2] Git Pull (csak fast-forward, a helyi modositasok megmaradnak)...
"%SSH%" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && B=$(git branch --show-current) && echo Ag: $B && git fetch origin && git merge --ff-only origin/$B"
if %errorlevel% neq 0 (
    echo.
    echo HIBA: a frissites nem sikerult ^(pl. elagazott a tablet aga, vagy nem erheto el^).
    echo A szervert NEM kell ujrainditani, a regi kod maradt.
    pause
    exit /b 1
)
echo [2/2] Adatbazis migratio...
"%SSH%" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && python migrate_db.py"

echo.
echo Az aktualis verzio a Tableten:
"%SSH%" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git branch --show-current && git log -1 --oneline"
echo.
echo A frissites befejezodott. Az uj kod a szerver ujrainditasa utan el:
echo tablet_stop_kepnezegeto.bat, majd tablet_start_kepnezegeto.bat
pause
