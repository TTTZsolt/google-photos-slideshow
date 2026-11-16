# Implementation_plan.md

## V16.3.8 — A felvétel ideje (`creation_time`) javítása

Branch: `16.3.8` (verzió: `16.3.8-dev`). Állapot: **jóváhagyásra vár**.

### Probléma

A `media_items.creation_time` a vetítés dátumszűrőjének (Utolsó hónap/hét/nap, kézi tartomány)
alapja, és a dokumentáció szerint a felvétel ideje. A B2-szinkron (`backend/worker.py:144`)
azonban a **B2 feltöltési időt** írja bele, és `db.merge`-dzsel felülírja a helyes értéket is
(a `incoming_processor.py` helyesen állítja be). Következmény: a Takeout-ból feltöltött régi
képek az „Utolsó hónap" szűrőben jelennek meg, ha az elmúlt hónapban töltöttük fel őket.

### Döntések (Zsolt, 2026-11-15)

- Az időt **helyi időben** tároljuk (naiv helyi `datetime`, mint a meglévő kód mindenhol).
- Ahol nem állapítható meg a felvétel ideje, a kép **kimarad a dátumszűrőből** (`creation_time = NULL`).
- A dátumszűrőnek **csak a telefonról érkező (friss) képeknél** kell pontosnak lennie. A Takeout-képek biztosan
  régebbiek egy hónapnál, ott a pontosság nem szempont: nem kell velük külön bajlódni, a dry-run sem foglalkozik velük.

### Megoldás

1. **Új függvény**: `backend/utils/media_dates.py` → `derive_capture_date(file_name)`.
   A Takeout-feltöltő által épített útvonalból (`ÉÉÉÉ/HH/[NN-album/]fájlnév`) és a fájlnévből
   számol, B2-letöltés nélkül. Sorrend:
   1. Fájlnévi `ÉÉÉÉHHNN[-_]ÓÓPPMM` (pl. `20170608-211651-0.jpg`, `IMG_20211224_181930.jpg`),
      **ha a dátuma egyezik az útvonal évével és hónapjával** (és napjával, ha az útvonal a napot is
      tartalmazza). Ekkor pontos dátum és idő.
   2. Útvonal napja (`ÉÉÉÉ/HH/NN-album/…`): az adott nap, 00:00.
   3. Csak év/hónap ismert (a fájlnév nem segít): **NULL** (kimarad).
   4. Nincs értelmezhető útvonal: **NULL**.
   A 3–4. eset a régi (Takeout) képeknél fordul elő, ezek a szűrő szempontjából érdektelenek, ezért nem kapnak külön kezelést.
   Ha a fájlnévi dátum nem egyezik az útvonallal, az **útvonal az irányadó** (a feltöltő eszköz
   EXIF → Takeout JSON → fájlnév sorrendben számolta, tehát megbízhatóbb).
2. **`worker.py`**: a feltöltési időt többé nem használja. A `creation_time` értéke:
   - a már meglévő érték, ha az egyezik az útvonal évével és hónapjával (megőrzi pl. a telefonos
     képek pontos EXIF-idejét), különben
   - `derive_capture_date(file_name)` eredménye (lehet NULL).
3. **Egyszeri javító szkript**: `scratch/backfill_creation_time.py`. Ugyanazt a függvényt és
   szabályt használja a meglévő sorokra.
   - Alapértelmezett **dry-run**: kiírja a változó sorok számát, és a **friss képekről** (az útvonal szerint az
     elmúlt ~3 hónapból, azaz a telefonról érkezőkről) részletesen mutat előtte/utána példákat. A régi képeknél csak
     összesítést ad. CSV-t ment a változásokról.
   - `--apply`: előtte `photos_app.db.backup-before-creation-time-ÉÉÉÉHHNN-ÓÓPPMM` biztonsági másolatot
     készít, majd kötegelve ír.
4. **Tesztek**: `scratch/test_media_dates.py` (sima Python assert, a `teszt_terv.md`-be is bekerül):
   a fenti ágak, az eltérő fájlnév/útvonal, a hibás vagy hiányzó útvonal, HEIC→JPG nevek.
5. **Dokumentáció**: `verziokontroll.md` (V16.3.8 + commit-tábla), `user_guide.md` 11. pont
   (a dátumszűrő a felvétel ideje alapján szűr, dátum nélküli képek kimaradnak),
   `specification.md` 11. pont.

### Nem változik

A `slideshow.py` lekérdezései maradnak: a NULL értékre a `>=`/`<` összehasonlítás hamis, ezért a
dátum nélküli kép magától kimarad a szűrt vetítésből. Dátumszűrő nélkül (Shuffle All) minden kép játszik.

### Kockázatok és bevezetés

- Az adatbázis módosítása éles adatot érint → mindig mentés előtte, a javító szkript alapból dry-run.
- A `main` és a tablet nem változik jóváhagyás nélkül. Sorrend: helyi teszt egy DB-másolaton →
  dry-run a tablet DB-jén (`tablet_teszt_branch.bat 16.3.8`) → te jóváhagyod → `--apply` →
  merge és éles frissítés csak a te kifejezett jóváhagyásod után.
- A telefonról érkező képeknél a szinkron már felülírta a pontos időt a feltöltési idővel. Ezeket a javító szkript a fájlnévből
  és az útvonalból állítja vissza. A dry-run friss képekre mutatott példái ezt ellenőrzik, mielőtt bármi íródik.

### Nyitott kérdés

Nincs.

---

## Korábbi terv (V16.1.x) — Takeout-feltöltés, szortírozás, kuka: végleges törlés nyomon követése

Branch: `16.1.5-dev`

## Cél / hosszú távú vízió (Zsolt, 2026-08-17)

A Lumina Képtár teljes munkafolyamata három lépésből álljon:

1. **Közvetlen feltöltés Takeout-ból** a B2-re (l. a `Fénykép előkészítés BlackBlaze-be
   másolás\takeout_to_b2_feltoltes.py` külön projektet és annak
   `Implementation_plan.md`/`tasks.md` fájljait — ez a rész ott zajlik).
2. **Szortírozás** a Luminában (meglévő funkció: Szortírozó, Mappa Kanban, AI-alapú
   előszűrés) — ideértve a **törlést** (kép a Lomtárba kerül).
3. **Lomtár ürítése** — a törlésre jelölt képek véglegesen eltávolítása a B2-ről.

**A hiányzó láncszem**: a Luminának emlékeznie kellene, mely képeket törölted
véglegesen, hogy egy **jövőbeli Takeout-feltöltés véletlenül ne töltse fel újra**
ugyanazt a (tartalmilag azonos) képet, amit tudatosan kiszelektáltál.

## Kutatási eredmény (2026-08-17) — jelenlegi állapot

- **`POST /api/trash/empty`** (`backend/routers/trash.py`) jelenleg **nyom nélküli,
  végleges törlést** végez: az adatbázisból törli a `MediaClassification` és
  `MediaItem` sorokat (`db.delete(...)`), a B2-n pedig azonnali, végleges
  `delete_file_version` hívást indít (ez **nem** ugyanaz, mint a B2 "hide" — az
   1 napos élettartam-szabály, amit a `set_b2_lifecycle.py` állít be, nem erre
  vonatkozik). **Semmi nem marad meg** a törölt tartalomról.
- **A `MediaItem` tábla jelenleg nem tárolja a SHA1-et**, pedig a B2 minden
  fájlnál natívan visszaadja azt (l. a Takeout↔B2 egyeztetési munka
  tapasztalata — `rclone lsjson --hash` ingyen adja).
- **Történeti nyom keresése**: a `log.txt`/`log.txt.1` naplók tartalmazzák a
  törölt fájlok teljes útvonalát (`b2_client.py` `delete_file_version` logolja),
  de csak két, egymástól elszakadó időablakban (2026.04.12–05.03 és
  2026.08.14-től) — a köztes kb. 3,5 hónapban (amikor feltehetően a nagyobb
  angliai törlés is történt) **nincs napló**. A meglévő két ablakban nem
  találtam angliai/londoni találatot. **Következtetés: a korábbi törlések
  konkrét listája feltehetően véglegesen elveszett**, ezt a tervet csak a
  jövőbeli törlésekre lehet alkalmazni.

## Javasolt architektúra

### 1. Új adatmodell: `DeletedContentHash`

Új tábla (`backend/models.py`), ami **túléli** a `MediaItem`/`MediaClassification`
törlését:

```python
class DeletedContentHash(Base):
    __tablename__ = "deleted_content_hashes"
    sha1 = Column(String, primary_key=True, index=True)
    last_known_file_name = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)  # pl. "trash-empty"
```

### 2. `MediaItem` kiegészítése SHA1 mezővel

- Új `sha1` oszlop a `MediaItem` táblán.
- A szinkron-worker (`backend/worker.py`, ami a B2-listázásból tölti fel a
  `MediaItem` táblát) mostantól elmenti a B2 által úgyis visszaadott
  content-SHA1-et is.
- Migráció szükséges a meglévő (már indexelt) sorokhoz is (utólagos
  backfill B2-lekérdezéssel, vagy csak az új szinkronoktól kezdve — ezt
  egyeztetni kell, l. Nyitott kérdések).

### 3. `empty_trash` kiegészítése

A `perform_physical_delete` háttérfeladat a tényleges B2-törlés **előtt**
(vagy közben, a már ismert `MediaItem.sha1`-ből) rögzíti a SHA1-et a
`DeletedContentHash` táblába — **mielőtt** a `MediaItem`/`MediaClassification`
sor törlődik.

### 4. Feltöltési oldal: duplikátum- és "szándékosan törölt" ellenőrzés

A `takeout_to_b2_feltoltes.py` (és bármilyen jövőbeli, hasonló feltöltő út)
minden fájl feltöltése előtt **két** forrást ellenőriz SHA1 alapján:
1. a jelenleg B2-n lévő tartalom (már megvan ez a logika),
2. **az új `DeletedContentHash` tábla** — ha egyezik, a fájl kihagyásra kerül,
   és a naplóban külön jelölve lesz ("szándékosan törölt, nem töltjük fel újra"),
   megkülönböztetve a sima "már fent van" esettől.

Mivel a `takeout_to_b2_feltoltes.py` egy másik, önálló projekt
(`Fénykép előkészítés BlackBlaze-be másolás`) alatt él, ehhez vagy közös
adatbázis-hozzáférésre, vagy egy egyszerű exportált SHA1-listára lesz
szükség a Lumina és a Takeout-feltöltő eszköz között — ezt tisztázni kell
(l. Nyitott kérdések).

## Nyitott kérdések (jóváhagyás előtt tisztázandó)

1. **Visszamenőleges SHA1-backfill**: a meglévő ~4979 `MediaItem` sorhoz
   utólag lekérjük a SHA1-et a B2-től (egyszeri migrációs script), vagy csak
   mostantól gyűjtjük?
2. **Lumina ↔ Takeout-feltöltő adatmegosztás**: a `DeletedContentHash` tábla a
   Lumina saját `photos_app.db`-jében lesz — a `takeout_to_b2_feltoltes.py`
   ezt közvetlenül olvassa (ugyanaz a `photos_app.db` fájl, Drive-szinkronizált),
   vagy inkább egy exportált CSV/JSON legyen a kapocs a két projekt között?
3. **Visszaállítás (Restore) hatása**: ha egy képet a Lomtárból visszaállítasz
   (nem ürítesz), az nem kerül a tombstone táblába — ez helyes, csak
   megerősítésre vár.

## Döntések (2026-08-17, jóváhagyva)

1. **Visszamenőleges SHA1-backfill**: igen — ehhez nem kellett külön script,
   mert a meglévő "Resync" funkció (`worker.py`) a B2-től úgyis lekéri az
   összes fájlt, és a `db.merge()` a meglévő sorokat frissíti. Egyszer
   lefuttatva (helyben tesztelve) mind a 4983 `MediaItem` sor megkapta a
   SHA1-et.
2. **Adatmegosztás**: B) exportált CSV (`deleted_sha1_list.csv`, a
   Képnézegető gyökerében), amit a `takeout_to_b2_feltoltes.py` olvas be.
   Az A) opciót (közös `photos_app.db` közvetlen olvasása) elvetettük, mert
   a DB WAL-módban fut, a Tabletről folyamatosan íródik, és a Drive-szinkron
   nem garantál konzisztens állapotot egy másik gépről olvasva.
3. **Visszaállítás hatása**: nincs teendő — a tombstone tábla kizárólag az
   `empty_trash` útvonalon íródik, a `restore` sosem éri el.

## Megvalósítás (2026-08-17)

- [x] `DeletedContentHash` modell hozzáadva (`backend/models.py`)
- [x] `MediaItem.sha1` oszlop hozzáadva
- [x] `worker.py`: a szinkron mostantól elmenti a B2-től kapott SHA1-et
- [x] `migrate_db.py` kiegészítve (új oszlop + 2 új tábla)
- [x] `trash.py` `empty_trash`: a végleges törlés előtt tombstone-t ír
  (DB + `deleted_sha1_list.csv`), csak akkor, ha még nincs meg az adott SHA1
- [x] `takeout_to_b2_feltoltes.py`: beolvassa a `deleted_sha1_list.csv`-t,
  és kihagyja (külön "szandekosan-torolve" státusszal jelölve) az egyező
  SHA1-ű fájlokat
- [x] Helyi teszt: migráció lefutott, szerver hiba nélkül elindult, Resync
  visszamenőleg feltöltötte mind a 4983 SHA1-et, a tombstone DB-írás és
  CSV-írás logikáját kitalált (nem valódi fotóhoz tartozó) SHA1-gyel
  leteszteltem és működik
- [x] **Éles teszt (2026-08-17, Zsolt által, PC-n futó dev-verzión)**: 4 valódi
  kép kiürítve a Lomtárból (`2011/09/25-kirandulas-etyek/p1160452.jpg`,
  `...460.jpg`, `...463.jpg`, `...468.jpg`). Ellenőrizve és mind stimmel:
  - mind a 4 SHA1 bekerült a `deleted_sha1_list.csv`-be
  - mind a 4 bejegyzés bekerült a `deleted_content_hashes` táblába
  - a `media_items`/`media_classifications` sorok ténylegesen törlődtek
  - a `log.txt` igazolja a tényleges B2-törlést (eredeti + thumbnail is)
  A funkció végponttól végpontig működik.
- [ ] `takeout_to_b2_feltoltes.py` frissített verziójának letesztelése a
  Lenovo-n (ahol a `pillow_heif` és a Takeout-fájlok is megvannak)

## Állapot

**Kódolás kész, helyi teszteléssel megerősítve.** Nincs még main-be
mergelve, nincs push-olva.
