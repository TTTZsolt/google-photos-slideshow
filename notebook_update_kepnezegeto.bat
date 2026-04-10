@echo off
echo --- Frissites: Slideshow Szerver a Notebookon ---
echo Pulling latest changes from GitHub...

:: Frissítés a jelenlegi branch-en
git fetch origin
git pull

echo.
echo A frissites (git pull) befejezodott.
echo.
echo Az aktualis verzio ezen a gepen:
git log -1 --oneline

echo.
echo Most mar elindithatod a helyi szervert a notebook_start_kepnezegeto.bat-tal!
pause
