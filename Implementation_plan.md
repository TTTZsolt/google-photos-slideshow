# Implementation_plan.md — Takeout-feltöltés, szortírozás, kuka: végleges törlés nyomon követése

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

## Állapot

**Tervezési fázis — jóváhagyásra vár.** Fejlesztés nem kezdődött el.
