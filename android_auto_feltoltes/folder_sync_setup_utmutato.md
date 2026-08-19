# FolderSync beállítása — Android automatikus fényképfeltöltés (B2 útvonal)

Ez az útmutató a **jelenlegi, ajánlott** módszert írja le: egy kész, Play Áruház-os
app (FolderSync) szinkronizálja a telefon kamera-mappáját közvetlenül a B2-re,
**eredeti fájlnévvel, feldolgozás nélkül** — a Lumina szerver dolgozza fel
utólag, automatikusan (l. `backend/incoming_processor.py`).

**Ez lecseréli** a korábbi, Termux-alapú megoldást (`user_guide.md` a
mappában) — nincs szükség Termux-ra, SSH-ra, csomagtelepítésre a telefonon.

**Fontos**: ez a leírás a FolderSync egy adott verziójának felülete alapján
készült — a pontos menüpont-elnevezések app-frissítés után kicsit eltérhetnek,
de a lényegi mezők (szerver cím, kulcsok, vödör/bucket név) mindig
megtalálhatók valamilyen hasonló elnevezéssel.

---

## 1. Előfeltétel: a hozzáférési adatok

Ezeket korábban már megkaptad/elmentetted (KeePass vagy más jelszókezelő):

| Mező | Érték |
|---|---|
| Endpoint / Server | `s3.eu-central-003.backblazeb2.com` |
| Access Key ID | `00349a10e344d8c0000000005` |
| Secret Access Key | *(a KeePass-edben elmentve — ez itt szándékosan nincs leírva)* |
| Bucket / vödör neve | `beerkezo` |
| Region | `eu-central-003` |

**2026-08-19-i pontosítás**: eredetileg egy csak a `beerkezo` vödörre
korlátozott kulcsot hoztunk létre biztonsági okból, de a B2 S3-kompatibilis
rétege "not entitled" hibával elutasítja a vödör-korlátozott kulcsokkal
végzett `ListBuckets` műveletet (amit a FolderSync a fiók teszteléséhez/
böngészéséhez használ) — ezért egy **teljes fiók-hozzáférésű** kulcsra
váltottunk (`...0005`). Ez technikailag minden vödrödet eléri, de **külön,
önállóan visszavonható** kulcs marad a fő alkalmazás-kulcsodtól.

---

## 2. A FolderSync telepítése

1. Nyisd meg a **Google Play Áruházat** a telefonodon.
2. Keress rá: **"FolderSync"** (fejlesztő: Tacit Dynamics / MJ Soft — a
   találati listában a legnépszerűbb, sok letöltéses találat lesz az).
3. Telepítsd (az ingyenes verzió is elég ehhez a feladathoz).
4. Első indításkor engedélyezd neki a **tárhely-hozzáférést** (a telefon
   fájljainak eléréséhez szükséges).

---

## 3. Fiók (Account) létrehozása — S3-kompatibilis kapcsolat

1. Nyisd meg a FolderSync-et, és keresd az **"Accounts"** (Fiókok) menüpontot
   (általában a bal oldali menüben, vagy a főképernyő tetején egy fül).
2. Nyomj a **"+" (hozzáadás)** gombra egy új fiók létrehozásához.
3. A felajánlott szolgáltatás-típusok listájában keresd az **"Amazon S3"**
   opciót (ha a FolderSync-ben nincs külön "Backblaze B2" vagy
   "S3 Compatible" opció, az "Amazon S3" a helyes választás — a B2
   S3-kompatibilis módban pontosan úgy viselkedik, mint az Amazon S3).
4. Add meg a mezőket:
   - **Account name**: bármilyen, neked beszédes név (pl. "Lumina beérkező")
   - **Access Key** / **Access Key ID**: `00349a10e344d8c0000000005`
   - **Secret Key** / **Secret Access Key**: a KeePass-ből másold be
   - **Server / Endpoint / Custom endpoint**: `s3.eu-central-003.backblazeb2.com`
     - Ha a FolderSync region-t is kér külön mezőben: `eu-central-003`
     - Ha van "Use HTTPS" vagy "SSL" kapcsoló: **kapcsold BE**
   - Ha van "Path style access" vagy hasonló kapcsoló, és a kapcsolódás
     nem sikerülne az alapértelmezett beállítással, próbáld meg ezt is
     bekapcsolni (B2 az S3-kompatibilis módban ezt néha megköveteli).
5. Mentsd el a fiókot. A FolderSync-nek ez után listáznia kellene a
   `beerkezo` vödröt, amikor a fiókon belül tallózol.

---

## 4. Szinkron-pár (Folder pair) létrehozása

1. A főképernyőn nyomj a **"+" (új mappapár)** gombra.
2. **Sync type**: válaszd a **"Upload only" / "Egyirányú feltöltés"** típust
   (a telefonról a felhő felé — soha nem szeretnénk, hogy a FolderSync
   bármit is visszatöltsön vagy töröljön a telefonon a felhő alapján).
3. **Local folder**: válaszd ki a telefon kamera-mappáját
   (általában `DCIM/Camera`).
4. **Remote folder**: válaszd a most létrehozott fiókot, és azon belül a
   `beerkezo` vödröt (a vödör gyökerét — ne hozz létre benne almappát,
   a szerver-oldali feldolgozó a vödör gyökerét nézi át).
5. **Fontos beállítások, amiket ellenőrizz**:
   - **"Delete source files after sync"**: hagyd **KIKAPCSOLVA** (a Lumina
     szerver törli majd a `beerkezo`-ból, miután feldolgozta — így ha a
     szerver-oldali feldolgozás valamiért elakadna, a fotó akkor is megvan
     a telefonon, nem vész el).
   - **"Overwrite files"**: mindegy, mert egyedi fájlnevek lesznek, de
     nyugodtan hagyhatod bekapcsolva.
   - **Fájltípus-szűrés** (ha van ilyen opció): állítsd be, hogy csak
     `.jpg`, `.jpeg`, `.png`, `.heic`, `.heif` fájlokat szinkronizáljon
     (a szerver-oldali feldolgozó úgyis kihagyja a többit, de érdemes
     már itt is szűrni, hogy ne próbáljon meg pl. videókat feltölteni).
6. **Ütemezés (Schedule)**:
   - Állíts be **időszakos automatikus szinkront**, pl. **15 percenként**
     (vagy amilyen gyakoriságot szeretnél — a Lumina szerver saját maga is
     csak 5 percenként néz rá a `beerkezo` vödörre, tehát ennél sűrűbb
     telefonos szinkronnak nincs értelme).
   - Ha a FolderSync támogatja az **"Instant sync" / "Fájlváltozás
     figyelése"** opciót (új fotó készülésekor azonnal szinkronizál, nem
     csak időszakosan), azt is bekapcsolhatod a gyorsabb feltöltésért.
7. Mentsd el a mappapárt.

---

## 5. Ki/bekapcsolás és utólagos (régebbi) képek feltöltése

### 5.1 Realtime feltöltés ki/bekapcsolása

Nincs szükség egyedi kapcsoló-fájlra vagy parancsra — ez **magában a
FolderSync appban** van:
- A mappapár melletti kapcsolóval, vagy a mappapárt hosszan nyomva
  **"Disable" / "Enable"** — ezzel csak azt a konkrét szinkront
  kapcsolod ki/be.
- Sok verzióban van egy **globális szünet-gomb** is (a főképernyőn vagy az
  értesítési sávban), ami minden szinkront egyszerre felfüggeszt.

### 5.2 Régebbi/kihagyott képek utólagos feltöltése

Hozz létre egy **második mappapárt** (ismételd meg a 4. fejezet lépéseit,
ugyanahhoz az S3-fiókhoz):

1. **Local folder**: egy dedikált mappa, pl. `Pictures/LuminaFeltoltes`
   (ha még nem létezik, hozd létre egyszer a Fájlkezelőben).
2. **Remote folder**: ugyanaz a `beerkezo` vödör, mint az elsőnél.
3. **Sync type**: ugyanúgy "Upload only", "Delete source files" kikapcsolva.
4. **Ütemezés**: ennél nyugodtan választhatsz **ritkább vagy csak kézi**
   indítást — nem kell folyamatosan futnia, csak amikor ténylegesen
   tettél bele valamit.

**Használat, amikor egy régebbi/kihagyott képet szeretnél feltölteni:**
1. Nyisd meg a telefon **Galéria/Fotók** appját, válaszd ki (akár többes
   kijelöléssel) a feltöltendő képe(ke)t.
2. **Megosztás → "Mentés eszközre" / "Másolás ide"** → válaszd a
   `Pictures/LuminaFeltoltes` mappát.
3. Nyisd meg a FolderSync-et, és nyomd meg ennél a mappapárnál a
   **"Sync now"** gombot (nem kell megvárnod az ütemezést).

A szerver ugyanazzal a logikával dolgozza fel, mint a kamera-mappából
érkező képeket — a `beerkezo` vödör nem tesz különbséget aközött, melyik
mappapár tette oda a fájlt.

---

## 6. Első teszt

1. Nyomd meg a mappapár melletti **"Sync now" / "Szinkronizálás most"**
   gombot (ne várj az ütemezésre).
2. A FolderSync mutatnia kell egy folyamatjelzőt, majd egy "Kész"/sikeres
   üzenetet.
3. Ellenőrizd a Lumina Dashboardon (vagy kérd meg Claude-ot), hogy a kép
   megjelent-e — a szerver legfeljebb 5 percen belül automatikusan
   feldolgozza, de manuálisan is kiváltható a feldolgozás azonnal:
   ```
   POST http://<tablet-ip>:8000/api/incoming/process-now
   ```
4. Ha minden jól ment, a kép a `kepek02`-ben, a helyes Év/Hónap mappában,
   besorolatlan állapotban jelenik meg — onnantól azonnal vetíthető, és
   opcionálisan a Mover + Szortírozó felületen kategorizálható.

---

## 7. Hibaelhárítás

- **"Connection failed" / nem sikerül csatlakozni a fióknál**: ellenőrizd,
  hogy pontosan másoltad-e be az Access Key ID-t és a Secret Key-t (nincs
  extra szóköz az elején/végén), és hogy az endpoint pontosan
  `s3.eu-central-003.backblazeb2.com` (HTTPS-sel, ha külön kérdezi).
- **A szinkron lefut, de a Luminában nem jelenik meg a kép**: nézd meg,
  hogy a fájl ténylegesen megérkezett-e a `beerkezo` vödörbe (B2 webes
  felületén), és hívd meg kézzel a `/api/incoming/process-now` végpontot —
  ha onnantól sem jelenik meg, a szerver oldali napló (`log.txt`) mutatja
  a hiba okát.
- **Csak néhány kép szinkronizálódik, a többi nem**: ellenőrizd a
  fájltípus-szűrőt (3. lépés) — lehet, hogy pl. `.png` vagy `.heic`
  ki van zárva a szűrőből.
