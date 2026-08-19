# Automatikus fényképfeltöltés - Tervezési jegyzet

Státusz: **Android: telepítve, tesztelve, élesben (fejlesztői ágon) automatikusan
működik, vég-a-végig ellenőrizve, valódi fotóval.** iPhone: még tervezés alatt.
Utolsó frissítés: 2026-08-19

## Android — jelenlegi, aktuális megoldás (2026-08-19)

**Egy korábbi, Termux-alapú próbálkozást** (saját `inotify`-figyelő szkript
a telefonon, SSH-hozzáféréssel a fejlesztéshez) **teljesen leváltottunk és
eltávolítottunk** — telepítése/karbantartása túl bonyolult lett volna egy
nem technikai felhasználó számára, ha ez egyszer termékké válna. A jelenlegi
megoldás:

- **Telefon oldal**: egy kész, Play Áruház-os app (**FolderSync**), S3-kompatibilis
  kapcsolattal — nincs Termux, nincs SSH, nincs csomagtelepítés a telefonon,
  csak egy app-telepítés és néhány beállítási mező. L. `android_auto_feltoltes/folder_sync_setup_utmutato.md`.
- **Célhely**: egy új, dedikált **`beerkezo`** B2-vödör — ide szinkronizál a
  FolderSync, **eredeti fájlnévvel, feldolgozás nélkül**.
- **Szerver oldal**: a Lumina backend (`backend/incoming_processor.py`) 5
  percenként automatikusan átnézi a `beerkezo` vödröt, és minden képet:
  SHA1-ellenőriz (duplikátum + "szándékosan törölt" tombstone-védelem),
  EXIF-dátum alapján Év/Hónap útvonalra rendez (`mappazasi_algoritmus_specifikacio.md`
  szerint, album nélküli ág — a kamera-mappa nem albumokba szervezett),
  bélyegképet generál, feltölti a `kepek02`-be, majd az adatbázis-rekordot
  is közvetlenül létrehozza (nem kell külön Sync-lépés).
- **Végtelen újra-feltöltés elleni védelem**: feldolgozás után az eredeti
  fájlt a `beerkezo`-ban **nem töröljük teljesen**, hanem egy **azonos nevű,
  0 bájtos helyjelölőre cseréljük** — a FolderSync (méret-ellenőrzés nélkül
  beállítva) így "már szinkronizált"-nak látja, és nem tölti fel újra
  minden alkalommal ugyanazt a képet.
- **Be/kikapcsolás és utólagos (régebbi) képek feltöltése**: mindkettő a
  FolderSync saját eszközeivel megoldható (mappapár ki/bekapcsolása, illetve
  egy második mappapár egy `Pictures/LuminaFeltoltes` mappához) — nem
  igényel egyedi kódot. L. `folder_sync_setup_utmutato.md` 5. fejezet.
- **Éles teszt eredménye**: valódi fotóval, teljesen automatikusan (a
  szerver 5 perces időzítője kapta el, kézi beavatkozás nélkül) működött —
  telefon → FolderSync → `beerkezo` → szerver-oldali feldolgozás → `kepek02`,
  helyes Év/Hónap mappában, azonnal vetíthető állapotban.
- **Megvalósítás helye**: `backend/incoming_processor.py`,
  `backend/models.py` (`B2Account.incoming_bucket_name`),
  `backend/main.py` (időszakos háttérfolyamat + `/api/incoming/process-now`
  manuális teszt-végpont), `android_auto_feltoltes/folder_sync_setup_utmutato.md`.
- **Még hátra van**: ez a funkció eddig csak a fejlesztői (`16.3.0-dev`) ágon
  fut, a Személyes PC-n — még nincs main-be mergelve/Tabletre telepítve.

## Cél

Amikor a feleség iPhone-ján vagy a saját Androidon egy fénykép készül, az automatikusan (emberi beavatkozás nélkül, vagy minimális beavatkozással) kerüljön fel a Luminába (B2 tárhelyre), hogy ne kelljen manuálisan exportálni/feltölteni.

## iPhone terv (még tervezés alatt, változatlan)

Az iOS sokkal korlátozottabb, mint az Android - nincs natív háttér-fájlrendszer-hozzáférés, és **nincs natív "óránként fusson le" ismétlődő trigger** a Shortcuts Personal Automation-okban (csak konkrét napszakra állítható, napi ismétléssel).

**Javasolt megoldás - eseményalapú trigger:**

1. Shortcuts app → Automatizálás fül → + → Személyes automatizálás létrehozása.
2. Trigger: **App → Kamera → Bezáródik** (közvetlenül azután fut le, hogy a felhasználó befejezte a fotózást és becsukta a Kamera appot - eseményvezérelt, nem fix időzítésű).
3. Akció: **"Fotók keresése"** (Find Photos), szűrve pl. "Készítés dátuma: ma" vagy egy elmentett utolsó-feltöltés-időbélyeg alapján, hogy csak az új képeket találja meg.
4. Akció: **"Tartalom lekérése URL-ről"** (Get Contents of URL) - POST metódus, multipart form-data, a talált fotó(k) mint payload, célcím: **még nyitott kérdés** — a mostani Android-megoldás mintájára itt is egy S3-kompatibilis app (ha van ilyen iOS-re), vagy a `beerkezo` vödör közvetlen elérése lenne a cél, nem egy egyedi `/api/upload` végpont (azt elvetettük az Androidos döntéssel összhangban).
5. Az automatizálás beállításainál ki kell kapcsolni a **"Futtatás előtt kérdezzen"** opciót, különben minden alkalommal meg kellene erősíteni egy értesítésben - kikapcsolva csendben, háttérben fut le.

**Alternatíva fix időzítéshez**: ha mégis inkább óránkénti fix időzítés kellene, azt csak 24 külön "Napszak" triggerű automatizálással lehet natívan megoldani (minden órára egy-egy) - működik, de körülményesebb, mint a "Kamera bezáródik" esemény.

**Alternatíva megbízhatóbb háttérműködéshez**: fizetős harmadik féltől származó app (pl. PhotoSync), ami már megoldja az iOS háttérkorlátozásait - ha a Shortcuts-alapú megoldás nem elég megbízható a gyakorlatban.

## Nyitott kérdések / következő lépések

- [x] ~~Fő döntés: épüljön-e saját `/api/upload` végpont?~~ **Nem** — a `beerkezo` vödör + szerver-oldali feldolgozó lett a megoldás, nem kellett hozzá egyedi feltöltő végpont.
- [x] ~~Android: Termux+inotify szkript, vagy Tasker app?~~ **Egyik sem** — kész, Play Áruház-os S3-kompatibilis szinkron-app (FolderSync) lett a végleges megoldás.
- [x] ~~Duplikátum-kezelés~~ — SHA1-alapú, megoldva (l. fent).
- [ ] iPhone: eseményalapú (Kamera bezárás) vagy fix óránkénti (24 automatizálás) trigger, és milyen S3-kompatibilis (vagy más) app érhető el iOS-en a `beerkezo` vödörhöz való feltöltéshez?
- [ ] Ez a funkció main-be mergelése és Tabletre telepítése (jelenleg csak a `16.3.0-dev` ágon, a Személyes PC-n fut).
