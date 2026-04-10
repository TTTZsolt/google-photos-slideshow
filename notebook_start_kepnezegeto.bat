@echo off
echo --- Inditas: Slideshow Szerver a Notebookon ---
echo Belso inditas folyamatban...

:: Szerver indítása a háttérben (külön ablak nélkül a start /b használatával)
:: Megjegyzés: A python -m backend.main parancsot használjuk
start /b python -m backend.main

echo.
echo Szerver elinditva a hatterben.
echo Varok 3 masodpercet a betoltesre...
timeout /t 3 /nobreak >nul

echo.
echo Lumina megnyitasa a Chrome-ban...
start chrome http://localhost:8000/

echo.
echo Kesz! A szerver fut ezen a gepen.
echo (Ez az ablak bezarhato, a szerver a hatterben marad)
pause
