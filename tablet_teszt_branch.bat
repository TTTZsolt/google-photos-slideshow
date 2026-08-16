@echo off
setlocal

if "%~1"=="" (
    echo HASZNALAT: tablet_teszt_branch.bat ^<branch-nev^>
    echo Pelda:     tablet_teszt_branch.bat ai-valogatas-javitas
    echo.
    echo Ez a script egy TETSZOLEGES git branch-et tolt fel es indit el a
    echo Tableten teszteles celjabol - NEM a main-t. A Tablet elesuzemi
    echo allapota csak addig valtozik, amig vissza nem valtasz main-re.
    pause
    exit /b 1
)

set BRANCH=%~1

echo --- TESZT-DEPLOY a Tabletre: %BRANCH% ---
echo FIGYELEM: ez most felulirja a Tableten fuzto verziot egy teszt-branch-csel!
echo.

where ssh >nul 2>nul
if %errorlevel% equ 0 (
    set SSH=ssh
) else (
    set SSH="C:\Program Files\Git\usr\bin\ssh.exe"
)

echo [1/5] Szerver leallitasa...
%SSH% -p 8022 u0_a116@192.168.1.157 "catt stop && (pkill -f 'python -m backend.main' || true)"

echo.
echo [2/5] Branch fetch + checkout: %BRANCH%
%SSH% -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && git fetch origin && git checkout %BRANCH% && git pull origin %BRANCH%"
if %errorlevel% neq 0 (
    echo.
    echo HIBA: nem sikerult atvaltani/pull-olni a(z) %BRANCH% branch-et.
    echo Ellenorizd, hogy a branch letezik-e es fel van-e pusholva a GitHub-ra.
    pause
    exit /b 1
)

echo.
echo [3/5] Adatbazis migracio...
%SSH% -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && python migrate_db.py"

echo.
echo [4/5] Szerver inditasa...
%SSH% -p 8022 u0_a116@192.168.1.157 "termux-wake-lock && cd ~/swift-newton && nohup python -m backend.main > /dev/null 2>&1 < /dev/null & exit"

timeout /t 3 /nobreak >nul

echo.
echo [5/5] Dashboard megnyitasa...
start chrome http://192.168.1.157:8000/

echo.
echo ====================================================================
echo   A TABLET MOST TESZT MODBAN FUT: %BRANCH%
echo   Ez NEM az eles (main) verzio!
echo.
echo   Ha vegeztel a tesztelessel, valts vissza az eles verziora:
echo     tablet_update_kepnezegeto.bat   (mindig a main-t huzza le)
echo     tablet_start_kepnezegeto.bat    (elinditja)
echo ====================================================================
pause
