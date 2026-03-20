@echo off
echo --- Inditas: Slideshow Szerver a Tableten ---
echo Csatlakozas es inditas...

:: Szerver indítása a háttérben (nohup)
:: Megprobaljuk a rendszer SSH-t
where ssh >nul 2>nul
if %errorlevel% equ 0 (
    ssh -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && nohup python -m backend.main > sys_log.txt 2>&1 < /dev/null & exit"
) else (
    echo A rendszer SSH nem talalhato, probalom a Git mappabol...
    "C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && nohup python -m backend.main > sys_log.txt 2>&1 &"
)

echo.
echo Szerver inditasi parancs elkuldve.
echo Varok 3 masodpercet, hogy biztosan elinduljon...
timeout /t 3 /nobreak >nul

echo.
echo Control Center megnyitasa a Chrome-ban...
start chrome http://192.168.1.157:8080

echo.
echo Kesz! A szerver fut a hatterben.
echo (A fekete ablak bezarhato)
pause
