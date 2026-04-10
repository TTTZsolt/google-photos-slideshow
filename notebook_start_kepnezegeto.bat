@echo off
setlocal
cd /d "%~dp0"
echo --- Inditas: Slideshow Szerver a Notebookon ---
echo Belso inditas folyamatban...

:: Szerver indítása a háttérben
start "Lumina Backend" /b python -m backend.main

echo.
echo Szerver inditasi parancs vegrehajtva.
echo Varok 3 masodpercet, hogy biztosan elinduljon...
timeout /t 3 /nobreak >nul

echo.
echo Lumina megnyitasa a Chrome-ban...
start chrome http://localhost:8000/

echo.
echo Kesz! A szerver fut a hatterben.
echo (A fekete ablak bezarhato)
pause
