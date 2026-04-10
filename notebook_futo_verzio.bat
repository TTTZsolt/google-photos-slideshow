@echo off
setlocal
cd /d "%~dp0"
echo --- Notebook: Aktiv verzio es allapot lekerdezese ---

:: Verziószám kinyerése a main.py-ből PowerShell segítségével
for /f "usebackq tokens=*" %%i in (`powershell -Command "(Select-String -Path 'backend/main.py' -Pattern 'V[0-9.]+').Matches.Value"`) do set VERSION=%%i

echo Verzio: %VERSION%

:: Leírás kinyerése a README.md-ből (a korábban közösen rögzített táblázat alapján)
echo | set /p="Leiras: "
powershell -Command "$v='%VERSION%'; $found = Select-String -Path 'README.md' -Pattern \"\*\*$v\*\*\"; if ($found) { $found.Line -replace '.*: ', '' } else { 'Nincs leiras' }"

echo.
echo --- Git Info ---
echo | set /p="Branch: "
git rev-parse --abbrev-ref HEAD
echo | set /p="Commit: "
git log -1 --oneline

echo.
echo --- Szerver Statusz ---
powershell -Command "$p=Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*backend.main*'}; if ($p) { write-host 'A SZERVER FUT' -ForegroundColor Green } else { write-host 'A SZERVER NEM FUT' -ForegroundColor Red }"

echo.
pause
