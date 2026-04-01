# 1. Cím és Dátum: 
**Google Photos Slideshow / Képnézegető - Tárhely és Chromecast (Catt) Hibaelhárítás**  
**Dátum:** 2026-03-24

---

# 2. Projekt kontextus
**Hol indultunk?**  
A Képnézegető alkalmazás Web UI felületén a TV keresés (Chromecast / `catt scan`) hiba nélkül, de üres listával ("No TVs found on network") tért vissza. Az oknyomozás kiderítette, hogy a Python backend (ami egy törött kijelzős Android / Termux tableten fut SSH-n keresztül) fizikailag nem volt képes ideiglenes hálózati cache fájlokat létrehozni a TV kereséshez, mivel a tablet beépített SSD meghajtója **100%-osan (0 byte szabad hellyel) megtelt (110 GB / 110 GB)**. 

**Cél:** A 110 GB tárhelyet lefoglaló anomália felderítése úgy, hogy a tableten nincs Root hozzáférés, és a képernyője törött, míg a Termux homokozója (sandbox) önmagában csak 2 GB-ot használt a fájlrendszerből. A hibát tovább bonyolította, hogy a képernyőtükröző `scrcpy` indítása is elhasalt a szabad hely hiánya miatt.

---

# 3. Meghozott döntések
*   **Android Cache ürítése távolról:** A képernyőtükrözés hiányában ADB (Android Debug Bridge) shell hívásokkal, parancssorból ürítettük a Chrome és egyéb futó böngészők adatait a minimális hely biztosítására.
*   **Fájlrendszer mélyfúrása:** Mivel a felhasználó saját filmgyűjteménye a tableten mindössze 35 GB-ot tett ki, a fennmaradó 75 GB sorsát az ADB `dumpsys diskstats` funkciójával, Root jogok nélkül világítottuk át, így az Android OS natív adathasználati eloszlását vizsgáltuk.
*   **A valódi szűk keresztmetszet azonosítása (Deleted Open File Leak):** Kiderült, hogy egy korábban manuálisan, futás közben "törölt" 30 GB-os naplófájl (`sys_log.txt`) továbbra is növekedett a háttérben, mivel befagyott, zombi alfolyamatok (PIDs) tartották nyitva a fájlleírókat (file descriptors). 
*   **Logolás átállítása:** A folyamatos memóriatúlcsordulás megelőzése érdekében a `start_tablet.bat` indítófájlban a `sys_log.txt`-be írást kiiktattuk. A jövőben csak a hasznos hibaüzeneteket tartalmazó, belsőleg limitált méretű (5 MB rotating) `log.txt` dokumentálja az alkalmazást, míg a konzol kimenet a "fekete lyukba" (`/dev/null`) kerül.

---

# 4. Technikai részletek/Kódok

**1. ADB alapú Cache törlés (Root nélküli helytisztítás)**
```cmd
adb shell pm clear com.android.chrome
adb shell pm clear com.sec.android.app.sbrowser
adb shell pm clear de.ozerov.fully
```

**2. A megosztott tárhely (Filmek/Letöltések) pásztázása (Méret: Megabájtban)**
```cmd
adb shell "du -m /sdcard/* 2>/dev/null | sort -nr | head -n 15"
```

**3. Rendszerszintű Storage és App-Data riport lekérése**
```cmd
adb shell dumpsys diskstats
```

**4. A "Láthatatlan/Törölt" de még írás alatt álló fantomfájlok megkeresése (Termux/SSH ablakból)**
Amikor a `df -h` 100%-ot mutat, de a látható fájlok `du` mérete minimális:
```bash
ls -l /proc/*/fd/* 2>/dev/null | grep "deleted"
```

**5. Zombi TCP/File folyamatok manuális kilövése PIDs alapján**
```bash
kill -9 21000 21599 31794
```

**6. Véglegesített indító parancs (start_tablet_kepnezegeto.bat - Részlet)**
Helyes nohup futtatás SSH-n, bemenet-kimenet redirectálás a `/dev/null`-ba (hogy a távoli SSH kliens bontani tudja a kapcsolatot):
```bat
"C:\Program Files\Git\usr\bin\ssh.exe" -p 8022 u0_a116@192.168.1.157 "cd ~/swift-newton && nohup python -m backend.main > /dev/null 2>&1 < /dev/null & exit"
```

---

# 5. Aktuális állapot
*   A zombi folyamatok (`kill -9`) lelövése révén a beragadt 30 GB tárhely sikeresen és véglegesen **felszabadult**. A `df -h` használata jelenleg `73%`-os telítettséget és 30GB szabad helyet jelez.
*   A filmek/letöltések (`/sdcard/Download`) érintetlenül maradtak.
*   A `start_tablet_kepnezegeto.bat` javítva lett, így az induló Python folyamat nem generál több elszabadult `sys_log.txt` állományt.
*   A Képnézegető API (Python) hibátlanul, elegendő tárhellyel tud háttérfolyamatokat (`catt scan`) futtatni.

---

# 6. Következő lépések
*   **Felhasználói Tesztútvonal:** A `start_tablet_kepnezegeto.bat` indítását követően a Vezérlőpult (`http://192.168.1.157:8080`) felületén megnyomni a "Chromecast" gombot, és fizikailag bizonyítani a sikeres hálózati TV listázást.
*   **AI Ágens Instrukció:** Ha legközelebb hasonló "0 byte szabad hely" vagy Chromecast lefagyást észlel a rendszer ezen a Python webszerveren, a diagnosztikát azonnal a törölt The `sys_log.txt` (via `lsof` vagy `/proc/fd/`) keresésével kell kezdeni, mielőtt fájlok manuális törlését ('du/rm') javasolná az AI a megosztott mappákban.

---

# 7. Kulcsszavak
Képnézegető, Termux, Android Tablet, df -h, dumpsys diskstats, No space left on device, nohup null, deleted open file leak, SSH background, Chromecast catt scan, pychromecast, server.log spam.

---

# 8. Későbbi incidens (2026-03-30): `server.log` végtelen hurok
**Jelenség:** A tablet ismét 100%-osan megtelt (0 byte szabad hely).
**Ok:** Bár a `sys_log.txt` korábban javítva lett, a `~/swift-newton/server.log` állomány teljesen betöltötte a Termux mappáját (31 GB méretre duzzadva). Ezt a `pychromecast` modul folyamatos és agresszív hibajelentése okozta egy leszakadt Chromecast hálózati kapcsolat után (végtelen újrapróbálkozási hurok: `AssertionError: Zeroconf instance loop must be running`).
**Megoldás:**
1. A fájlt TILOS `rm`-mel törölni, mert ha a folyamat nyitva tartja, ismét rejtett tárhely-szivárgást okoz. Szimplán le kell nullázni SSH-n keresztül: `> ~/swift-newton/server.log`
2. Ezt követően a Python webszervert újra kell indítani a folyamatos naplózás megszakítása és a Chromecast kapcsolat tiszta újraépítése érdekében (a Windows gépen futtatható `stop_tablet.bat` és `start_tablet.bat` segítségével).

---

# 9. Végleges javítás (2026-04-01): Chromecast kimenetének némítása
**Megoldás a hurokra:** A `pychromecast` és a `catt` (Cast All The Things) parancssori hibákat okozó végtelen ciklusának kimenetét ("AssertionError: Zeroconf instance loop must be running") programkódon belül `/dev/null`-ba (`subprocess.DEVNULL`) irányítottuk. 

A `backend/routers/dashboard.py` fájlban a Chromecast indításáért felelős `subprocess.Popen("catt"...)` parancsot kiegészítettük az `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` attribútumokkal. Emellett a `main.py`-ban lejjebb vettük a `zeroconf` és `pychromecast` loggerek érzékenységét `CRITICAL` szintre. Így a hiba továbbra is megtörténhet (ha megszakad a hálózat), de a rendszer nem árasztja el többé hibaüzenetekkel a Termux `server.log`-ját, megvédve a tablet 110 GB-os háttértárát.
