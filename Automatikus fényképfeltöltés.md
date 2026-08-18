# Automatikus fényképfeltöltés - Tervezési jegyzet

Státusz: **Android: kód elkészült, telepítésre/tesztelésre vár. iPhone: még tervezés alatt.**
Utolsó frissítés: 2026-08-18

## Android — döntések és megvalósítás (2026-08-18)

- **Fő döntés**: nem épült saját `/api/upload` végpont — a platformspecifikus (`rclone`-alapú Termux-szkript) út mellett döntöttünk, mert egyszerűbb és nem igényel backend-fejlesztést.
- **Android eszköz**: Termux + `inotify-tools` szkript (nem Tasker) — így a kód verziózható, git alatt tartható, és konzisztens a projekt többi Termux-alapú eszközével (Tablet, SSH).
- **Célhely**: közvetlenül a `Kepek02` vödör (**nem** a `forras` — annak, mint korábban tisztáztuk, már nincs aktív szerepe), a `mappazasi_algoritmus_specifikacio.md` szerinti Év/Hónap struktúrával. Mivel a telefon kamera-mappája nem albumokba szervezett, mindig a sima EXIF-alapú (album nélküli) ág érvényesül.
- **Duplikátum-kezelés**: nem volt szükség külön megoldásra — a cél a `Kepek02`-ben minden fájl a saját Év/Hónap/névtisztított útvonalára kerül, natural key-ként működik (ha véletlenül kétszer töltődne fel ugyanaz, `rclone copyto` egyszerűen felülírja ugyanazon az útvonalon).
- **Be/kikapcsolható**: egyszerű jelzőfájl (`~/.lumina_auto_upload_enabled`) — a figyelő folyamat (`lumina_watcher.sh`) folyamatosan fut a háttérben (Termux:Boot indítja újraindítás után is), de csak akkor tölt fel, ha a jelzőfájl létezik.
- **Megvalósítás helye**: `android_auto_feltoltes/` mappa (`lumina_watcher.sh`, `start_auto_feltoltes.sh`, `stop_auto_feltoltes.sh`, `status_auto_feltoltes.sh`, `termux_boot_start_lumina_watcher.sh`, `user_guide.md`).
- **Ismert korlát**: csak valós idejű figyelés (`inotifywait`) — ha a folyamat leáll, a kimaradt időszak fotóit nem pótolja utólag automatikusan (l. `android_auto_feltoltes/user_guide.md`, "Ismert korlátok").
- **Még hátra van**: a telepítés és éles tesztelés a te saját Androidodon — ehhez nekem nincs hozzáférésem, a `user_guide.md` lépésről lépésre vezet végig rajta.

## Cél

Amikor a feleség iPhone-ján vagy a saját Androidon egy fénykép készül, az automatikusan (emberi beavatkozás nélkül, vagy minimális beavatkozással) kerüljön fel a Luminába (B2 tárhelyre), hogy ne kelljen manuálisan exportálni/feltölteni.

## Két lehetséges architektúra-irány

1. **Platformspecifikus, kész eszközök** (nincs backend-fejlesztés, gyorsabb):
   - Android: `rclone` közvetlenül a B2-re.
   - iPhone: Shortcuts automatizálás vagy fizetős app (pl. PhotoSync).
   - Hátrány: két teljesen külön útvonalat kell karbantartani, és a képek nem mennek át a Lumina saját adatbázis-logikáján (MediaItem/MediaClassification rekordok létrehozásán), tehát utólag esetleg szükség lehet egy szinkronizáló/scannelő lépésre, hogy a Lumina "észrevegye" az új fájlokat.

2. **Saját upload API végpont a Lumina backendben** (pl. `POST /api/upload`, multipart form-data-val):
   - Mindkét platform ugyanoda küldene, egységesebb.
   - A backend azonnal létre tudja hozni a megfelelő MediaItem/MediaClassification rekordot is, nem csak a fájlt tolja fel.
   - Hátrány: ezt még meg kell tervezni és megírni (jelenleg nem létezik).
   - **Ez még nyitott döntés, hogy szükséges-e, vagy elég a platformspecifikus út.**

## Android terv

A tableten már fut Termux, ez természetes alapot ad:

- `inotify-tools` csomag (`pkg install inotify-tools`) egy háttérben futó szkripttel:
  `inotifywait -m -e create ~/storage/dcim/Camera/` figyeli a kamera-mappát, és minden új fájlnál lefuttat egy feltöltést (pl. `curl -F "file=@ujfoto.jpg" http://lumina-url/api/upload`, vagy közvetlen `rclone` hívás a B2-re).
- `Termux:Boot` gondoskodik róla, hogy a figyelő szkript telefon-újraindítás után is automatikusan elinduljon.
- **Alternatíva kódolás nélkül**: Tasker app, ami natívan tud "új fotó készült" eseményre HTTP POST-ot küldeni - nem igényel Termux-szkriptet.

## iPhone terv

Az iOS sokkal korlátozottabb, mint az Android - nincs natív háttér-fájlrendszer-hozzáférés, és **nincs natív "óránként fusson le" ismétlődő trigger** a Shortcuts Personal Automation-okban (csak konkrét napszakra állítható, napi ismétléssel).

**Javasolt megoldás - eseményalapú trigger:**

1. Shortcuts app → Automatizálás fül → + → Személyes automatizálás létrehozása.
2. Trigger: **App → Kamera → Bezáródik** (közvetlenül azután fut le, hogy a felhasználó befejezte a fotózást és becsukta a Kamera appot - eseményvezérelt, nem fix időzítésű).
3. Akció: **"Fotók keresése"** (Find Photos), szűrve pl. "Készítés dátuma: ma" vagy egy elmentett utolsó-feltöltés-időbélyeg alapján, hogy csak az új képeket találja meg.
4. Akció: **"Tartalom lekérése URL-ről"** (Get Contents of URL) - POST metódus, multipart form-data, a talált fotó(k) mint payload, célcím a Lumina `/api/upload` végpontja.
5. Az automatizálás beállításainál ki kell kapcsolni a **"Futtatás előtt kérdezzen"** opciót, különben minden alkalommal meg kellene erősíteni egy értesítésben - kikapcsolva csendben, háttérben fut le.

**Alternatíva fix időzítéshez**: ha mégis inkább óránkénti fix időzítés kellene, azt csak 24 külön "Napszak" triggerű automatizálással lehet natívan megoldani (minden órára egy-egy) - működik, de körülményesebb, mint a "Kamera bezáródik" esemény.

**Alternatíva megbízhatóbb háttérműködéshez**: fizetős harmadik féltől származó app (pl. PhotoSync), ami már megoldja az iOS háttérkorlátozásait - ha a Shortcuts-alapú megoldás nem elég megbízható a gyakorlatban.

## Nyitott kérdések / következő lépések

- [ ] **Fő döntés**: épüljön-e saját `/api/upload` végpont a Lumina backendbe, vagy elég a platformspecifikus eszközökre (rclone + Shortcuts/PhotoSync) támaszkodni?
- [ ] Android: Termux+inotify szkript, vagy Tasker app? (kódolás vs. no-code)
- [ ] iPhone: eseményalapú (Kamera bezárás) vagy fix óránkénti (24 automatizálás) trigger?
- [ ] Ha saját API végpont mellett döntünk: hogyan történjen az azonosítás/autentikáció (ki, melyik eszközről tölt fel), hogy ne lehessen illetéktelenül feltölteni?
- [ ] Ha saját API végpont mellett döntünk: milyen mappaszerkezetbe/dátum alapú elrendezésbe kerüljenek az új képek a B2-n (hasonlóan a meglévő Takeout-feltöltő logikához)?
- [ ] Duplikátum-kezelés: mi történjen, ha ugyanaz a kép (pl. iCloud és Android is szinkronizálja egy közös albumot) mindkét eszközről feltöltésre kerül?
- [ ] A tényleges `/api/upload` végpont kódja még nincs megírva.
