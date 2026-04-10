@echo off
setlocal
cd /d "%~dp0"
echo --- Frissites: Slideshow Szerver a Notebookon ---
echo Pulling latest changes from GitHub...

:: Lekérjük az aktuális branch nevet
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
echo Aktualis ag: %BRANCH%

:: Frissítés a jelenlegi branch-en
git fetch origin
git pull origin %BRANCH%

echo.
echo A frissites befejezodott.
echo.
echo Az aktualis verzio ezen a gepen:
git log -1 --oneline

echo.
echo Most mar elindithatod a helyi szervert a notebook_start_kepnezegeto.bat-tal!
pause
