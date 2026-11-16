@echo off
setlocal
rem Lumina - automatikus tesztek futtatasa.
rem A virtualis kornyezet a Google Drive-on KIVUL van (sok ezer fajl, a Drive nem birja),
rem elso futasnal automatikusan letrejon. Hasznalat:  tests\run_tests.bat
rem A "sqlalchemy<2.1" szandekos: a 2.1 natív DLL-jét a Windows alkalmazas-vezerlese blokkolhatja,
rem a 2.0.x tiszta Python tartalekra esik vissza.

set VENV=%USERPROFILE%\venvs\kepnezegeto-test
set ROOT=%~dp0..

if not exist "%VENV%\Scripts\python.exe" (
    echo [Elso futas] Tesztkornyezet letrehozasa: %VENV%
    python -m venv "%VENV%" || (echo HIBA: nem sikerult a venv letrehozasa & exit /b 1)
    "%VENV%\Scripts\python.exe" -m pip install -q -r "%ROOT%\requirements.txt" "sqlalchemy<2.1" pytest || (echo HIBA: telepites & exit /b 1)
)

cd /d "%ROOT%"
"%VENV%\Scripts\python.exe" -m pytest tests -q -p no:cacheprovider %*
exit /b %errorlevel%
