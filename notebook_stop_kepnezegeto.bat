@echo off
setlocal
echo --- Leallitas: Slideshow Szerver a Notebookon ---

:: A python folyamat leállítása, amely a backend.main-t futtatja
echo Helyi szerver keresese es leallitasa...

:: Megkeressük a 8000-es porton hallgatózó folyamatot és leállítjuk
echo Keressük a 8000-es porton futó folyamatot...
powershell -Command "$p = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if($p) { Write-Host 'Folyamat megtalalva (PID: ' $p.OwningProcess '), leallitas...'; Stop-Process -Id $p.OwningProcess -Force } else { Write-Host 'Nem talalható folyamat a 8000-es porton.' }"

echo.
echo Leallitasi parancs vegrehajtva.
pause
