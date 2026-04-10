@echo off
setlocal
echo --- Leallitas: Slideshow Szerver a Notebookon ---

:: A python folyamat leállítása, amely a backend.main-t futtatja
echo Helyi szerver keresese es leallitasa...

:: Megkeressük és leállítjuk a specifikus folyamatot PowerShell segítségével
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*backend.main*'} | Stop-Process -Force"

echo.
echo Leallitasi parancs vegrehajtva.
pause
