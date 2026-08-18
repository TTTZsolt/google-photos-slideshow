Ez a dokumentum követi a Lumina projekt mérföldköveit és fejlesztési szakaszait.

1. Kérlek minden fejlesztési lépésről készíts egy commit-ot magyarázó szöveggel.
2. Mindíg ajánlj fel egy magyarázó szöveget és legyen lehetőségem azt átfogalmazni.
3. Készíts táblázatot a commit-okról egy verzión belül: minden commitnak legyen egysora: verzió szám, commit szám és a magyarázó szöveg.
4. A commit táblázatot a Lumina Képtár Commit fejezetben helyezd el.
5. A fő verziók és magyarázatuk továbbra is a Verziótörténet fejezetben kerüljön felsorolásra.

# Lumina Képtár - Verziótörténet

## [V16.2.1] - Forrás vödör szerepének megszüntetése (2026-08-18)

- **Felismerés**: átfogó kódvizsgálat kimutatta, hogy a `forras` (staging) vödörnek a Zero-Move architektúra (V15.8.4) óta gyakorlatilag nincs önálló, szükséges szerepe — a Mover és a legtöbb folyamat már közvetlenül a `kepek02`-vel dolgozik.
- **Zero-Move Lomtár-visszaállítás**: a `POST /api/trash/restore/{id}` és `/api/trash/restore-all` mostantól közvetlenül a `kepek02`-be állítja vissza a képet, nem a `forras`-on keresztül (eggyel kevesebb fizikai B2-mozgatás).
- **Dokumentáció frissítése**: `DOKUMENTACIO.md` és `README.md` pontosítva — világosan szétválasztva a jelenlegi elsődleges út (közvetlen `kepek02`-feltöltés, azonnal vetíthető, kategorizálás opcionális a Mover-en keresztül) és a régebbi, ma is támogatott, de már nem szükséges `forras`-alapú út.

## [V16.1.0] - Fénykép válogatás AI segítségével (Fejlesztés alatt)

- **AI integráció**: Előkészítés a fényképek automatikus válogatására és elemzésére AI segítségével.
- **Függőségek**: A `google-generativeai` és `pillow` könyvtárak hozzáadása a háttérben futó AI elemzés javítására.
- **Tesztelés**: `teszt_terv.md` ellenőrző lista létrehozása a manuális ellenőrzéshez.
- **Modell frissítés**: A nem támogatott Gemini 1.5 modellek lecserélése és automatikus fordítása `gemini-2.5-flash` és `gemini-2.5-pro` modellekre.
- **Jóváhagyó felület**: Képnagyítás (modal popup) funkció hozzáadása a szortírozandó képekhez a részletesebb ellenőrzéshez.
- **Modell védelem (Fallback)**: Modell hiba esetén automatikus próbálkozás a fallback listáról (2.5, 2.0, flash-latest) a leállások elkerülésére.
- **Hibakezelés**: AI hibák rögzítése és mentése az adatbázis `ai_error` oszlopába a csendes "Bizonytalan" kategóriába bukás helyett.
- **Összes elvetése**: "Összes besorolás elvetése" gomb hozzáadása a jóváhagyó felülethez, ami visszaállítja a képeket besorolatlan állapotba, így a folyamat újraindítható.
- **AI kategória leírások**: A kategóriákhoz leírás adható, amelyeket a rendszer betáplál a Gemini promptba a pontosság javítására és a "Bizonytalan" kategória csökkentésére.
- **Progress Tracking**: Valós idejű haladási napló (progress bar) megjelenítése a Mover felületen és az AI Jóváhagyás felületen is, jelezve a háttérben futó AI szortírozás állapotát.
- **Mappaböngésző javítás (16.1.6)**: A Visszamozgató mappaböngészője eddig "elnyelte" azokat a képeket, amik egy mappában közvetlenül, album-alkönyvtár nélkül vannak (csak a szülőmappa összesítő számában jelentek meg, kattintható alkönyvtárként nem). Mostantól egy külön, nem kattintható sor is megjelenik: "Közvetlenül itt (alkönyvtár nélkül)", a besorolatlan/kategóriánkénti bontással.
- **Mappa Kanban lapozás javítása (16.1.7-16.1.8)**: A 100 képes limit fölötti mappáknál mentés után eddig ugyanaz a 100 kép jött vissza újra. A `/api/folders/items` végpont mostantól `offset` paramétert is fogad, a Mentés/Következő gomb pedig akkor is a következő adagra lép, ha az adott 100 közül semmit sem kellett módosítani.
- **Törlésre jelölt képek láthatósága (16.1.8)**: A Kanbanban törlendőnek jelölt (és emiatt azonnal a Kuka bucketbe mozgatott) képek eddig eltűntek a mappa nézetéből újranyitáskor. Mostantól a Kuka bucket is bekerül a lekérdezésbe, így a "Törlendő" oszlopban megmaradnak, amíg véglegesen nem törlöd őket a Kuka oldalon; a Besorolatlanba visszahúzott képek fizikailag is visszakerülnek a fő bucketbe.
- **Kép nagyítás - navigáció, forgatás, törlés (16.1.8-16.1.11)**: A Kanban nagyított képnézetében PageUp/PageDown lapoz a kategórián belüli szomszédos képekre, L/R billentyű elforgatja és el is menti a képet (valós idejű CSS-előnézettel, majd a ténylegesen elforgatott képre váltással, sorban feldolgozott gyors egymás utáni lenyomásokkal is), a Delete billentyű pedig a "Törlendő" oszlopba sorolja át a képet és a következőre lép.
- **Lomtárürítés adatvesztési hiba javítása (16.1.12)**: A "Kuka ürítése" eddig azonnal, az egész listára törölte az adatbázis-rekordokat, mielőtt a tényleges B2-törlés/nyilvántartásba-vétel (tombstone) a háttérben lefutott volna - egy félbeszakadt háttérfolyamat így "árva" fájlokat hagyhatott a Kuka bucketben, amikről az alkalmazás többé nem tudott. Mostantól az adatbázis-rekord törlése csak az adott fájl sikeres feldolgozása után történik meg, elemenként.

## [V16.0.0] - Zero-Move apró hibáinak javítása (2026-05-09)

- **Szortírozó**: Kijavítva a duplikált képek megjelenése (Concurrency Lock a pre-fetchingnél).
- **Szortírozó**: Új "Pánik gomb" a szortírozási várólista azonnali ürítéséhez.
- **Lomtár**: Fixálva a visszaállítási logika; a képek most már azonnal megjelennek a szortírozóban és a bélyegképeik is visszakerülnek a helyükre.
- **Stabilitás**: A háttérben futó "szellem-szerverek" okozta 404-es hibák elhárítva.

## [V15.8.4] - Zero-Move Mover és Párhuzamosítás (2026-05-09)

- **Architektúra**: Új "Zero-Move" logika bevezetése: a válogatás előkészítése (Bulk Reverse) immár azonnali, mert nem mozgatunk fizikai fájlokat, csak adatbázis állapotokat kezelünk.
- **Rendezés**: A Szortírozóban a képek könyvtárankénti és ABC sorrendben jelennek meg.
- **Sebesség**: Minden háttérben maradó B2 művelet (törlés, metaadat frissítés) párhuzamosított szálakon fut a reszponzivitás érdekében.
- **Egyszerűsítés**: A rendszer támogatja a közvetlenül a `kepek02` vödörbe történő feltöltést, a `forras` vödör használata már nem kötelező.

## [V15.8.3] - Szortírozó HD Zoom (2026-05-09)

- **Szortírozó**: Automatikus váltás az eredeti nagyfelbontású képre nagyításkor (pinch-to-zoom), így a részletek jobban láthatóak.

## [V15.8.2] - Mover Dokumentáció és Stabilitás (2026-05-09)

- **Dokumentáció**: Mover funkció (B2 fájlmozgatás és thumbnail szinkronizáció) részletes leírása a README-ben és a Dokumentációban.
- **Stabilitás**: Backend szerver "Internal Server Error" (zombi folyamat) elhárítása és újraindítása.

## [V15.8.1] - Univerzális Fejléc és Robusztus Lomtár (2026-05-04)

- **Navigáció**: SPA architektúra előkészítése központosított fejléc motorral.
- **Thumbnail Kezelés**: Kijavítva a Bulk Reverse hiba, ahol a thumbnail-ek nem mozogtak vissza a forrás vödörbe.
- **Lomtár Optimalizálás**: Azonnali adatbázis-szintű ürítés a reszponzívabb élményért; szinkronizált UI frissítés.
- **Stabilitás**: Javított hibatűrés az előnézeti képek betöltésekor.

## [V15.0] - Teljesítmény Optimalizálás (Thumbnail alapú betöltés) (2026-05-03)

- **Sebesség**: Drasztikusan gyorsabb Szortírozó és Lomtár a párhuzamos thumbnail vödrök használatával.
- **Adatkezelés**: Automatikus thumbnail mozgatás és törlés az eredeti fájlokkal összhangban.
- **UI**: Finomított betöltési indikátorok és áttűnések az előnézeti képeknél.

## [V14.3] - Verzió Egységesítés és Polírozás (2026-05-02)

- **Standardizálás**: A verziószámok egységesítése minden modulban V14.3-ra.
- **Dokumentáció**: README és verziótörténet frissítése.
- **V14.2 javítások**: Tartalmazza a V14.2-ből elmaradt apróbb simításokat.

## [V14.2] - 2026-05-02-i Stabil Verzió (Tablet alap)

- **Robusztus Szinkronizáció**: B2 Sync Progress Tracker (hőmérő) és hibatűrő kategória kezelés.
- **Ékezet-érzéketlen keresés**: Javított kategória felismerés a vetítő motorban.
- **Debug API**: Új `/api/debug/categories` végpont a kategóriák ellenőrzéséhez.

## [V14.1] - Szinkronizációs Hőmérő (2026-04-15)

- **Progress Tracking**: Vizualizált szinkronizációs haladás (hőmérő) a Connect oldalon.
- **Pontos számláló**: Valós idejű "X/Y items" kijelzés a B2 Node-oknál.
- **Adatbázis robusztusság**: Továbbfejlesztett migrációs adatszerkezet.

## [V14.0] - Immerzív Szortírozó és Undo Rendszer (2026-04-12)

- **Full Screen Szortírozó**: Teljes kijelzős nézet a fotók átnézéséhez, helytakarékos áttetsző ikonokkal.
- **Smart Undo (Visszavonás)**: Az utolsó művelet (osztályozás/törlés) azonnali javítása a kis előnézeti képre kattintva.
- **Lomtár Előnézet**: Törlésre jelölt képek nagy méretű ellenőrzése (Esc támogatás).
- **Adaptív UX**: Felhasználói szokásokhoz igazodó (tanuló) értesítési rendszer.

## [V13.8] - Felhő-szintű Metaadatok II. (2026-04-10)

- **Központi Szinkronizáció**: A kategóriák rögzítése a B2 fájlok metaadataiba (`X-Bz-Info-category`), így a munka eszközfüggetlenné vált.
- **Adat Migráció**: Szkript a meglévő helyi kategóriák felhőbe történő mozgatásához.

## [V13.5] - Felhő-szintű Metaadatok I. (2026-04-05)

- Megkezdődött az átállás a helyi adatbázisról a felhő-alapú kategória tárolásra.

## [V13.0] - Moduláris Dashboard (2026-04-01)

- **Új SPA Felület**: Moduláris Dashboard architektúra aszinkron adathozzáféréssel.
- **Photopea Integráció**: Megkezdődött a Digitális Labor modernizálása.

## [V12.0] - Interaktív Receiver (2026-03-25)

- **Távvezérlés**: "Következő kép" gomb a Slideshow felületén.
- **Proxy V2**: Optimalizált Cloudflare Proxy a gyorsabb képelérésért.

## [V11.0] - Dinamikus Kategóriák (2026-03-15)

- **Testre szabhatóság**: Egyedi kategóriák létrehozása egyéni ikonokkal, színekkel és nevekkel.

## [V10.0] - Gombos Szortírozó (2026-03-01)

- Bevezetésre került a gombokkal történő osztályozás a biztonságosabb bevitel érdekében.

## [V9.0] - Swipe Szortírozó (2026-02-15)

- Első Tinder-stílusú érintőképernyős válogató felület.

## [V8.3] - Hálózati Stabilitás (2026-02-01)

- **Catt Timeout Fix**: Stabilabb Chromecast kapcsolat és automatikus újracsatlakozás.
- **Screen Wake Lock**: Kijelző elsötétedés elleni védelem böngészőben.

## [V7.9] - Digitális Labor (2026-01-15)

- Megjelent a hibás képek megjelölése (Flagging) és a javítási várólista (Retouch Queue).

## [V3.0] - Alapkiadás (2025-12-01)

- Első stabil, B2 alapú, villódzásmentes slideshow motor.

# Lumina Képtár - Commit-ok

| Verzió  | Commit    | Magyarázat                                                                                     |
|:------- |:--------- |:---------------------------------------------------------------------------------------------- |
| V16.2.1 | `TBD`     | Dokumentáció frissítése: forras vödör szerepének pontosítása (DOKUMENTACIO.md, README.md)     |
| V16.2.1 | `2feedbe` | Zero-Move a Lomtárból visszaállításnál: kepek02-be közvetlenül, forras kihagyásával           |
| V16.1.0 | `a151660` | Fix: Az AI hibaállapotok megtartása az adatbázisban a részletes hibaüzenetek és hiba banner megjelenítéséhez |
| V16.1.0 | `ee048f3` | Fix: Böngésző lefagyások megszüntetése visibility- és modul-érzékeny setTimeout alapú lekérdezéssel |
| V16.1.0 | `2cdac25` | Feature: Felhasználó értesítése, ha az AI korlát miatt régebbi modellre váltott vissza         |
| V16.1.0 | `966333c` | Fix: Infinite loop hiba javítása a jóváhagyó felület aszinkron betöltésekor                    |
| V16.1.0 | `ff79293` | Fix: Sikertelen AI képek megtartása a Szortírozóban (is_in_sorter = 1)                         |
| V16.1.0 | `a48c85d` | Fix: AI hibaértesítő banner azonnali megjelenítése a jóváhagyó oldal betöltésekor              |
| V16.1.0 | `9510bb0` | Fix: AI jóváhagyásra váró képek kizárása a manuális Szortírozóból                              |
| V16.1.0 | `7237488` | Fix: AI hibaértesítő banner a jóváhagyó oldalon, és adatbázis tisztítás sikertelen AI után     |
| V16.1.0 | `2ec3db1` | Feature: AI progress bar, reject all és kategória leírások a Gemini prompt finomhangolásához   |
| V16.1.0 | `617791a` | Feature: AI modell védelmi rendszer (Fallback modellek, és hiba rögzítése)                    |
| V16.1.0 | `5233fd2` | Fix: AI modell frissítés Gemini 2.5-re és képnagyítás modal hozzáadása a jóváhagyó felülethez   |
| V16.1.0 | `c3eedf4` | Fix: Google Gemini API és Pillow függőségek pótlása, teszt terv létrehozása                    |
| V16.1.0 | `2e34e51` | Képválogatás AI segítségével fejlesztése                                                       |
| V16.0.0 | `V16`     | Zero-Move apró hibáinak javítása (Szortírozó duplikáció, Lomtár visszaállítás fix, Pánik gomb) |
| V15.8.4 | `3245dd5` | Rendszer dokumentáció frissítése az új Zero-Move és Single-Bucket munkafolyamathoz             |
| V15.8.4 | `e89dacb` | Zero-Move Sorter architektúra és párhuzamosított B2 műveletek implementálása                   |
| V15.8.3 | `645e544` | Szortírozó HD Zoom támogatás nagyításkor                                                       |
| V15.8.2 | `bb26c90` | Verziószám emelése V15.8.2-re a kódban és a dokumentációban                                    |
| V15.8.2 | `b75b1be` | Mover funkció részletes dokumentálása és szerver stabilitási javítás                           |
| V15.8.1 | `d6274f6` | Digitális Labor: Új retusálási mentési logika és fájlnév konvenció bevezetése                  |
| V15.8.1 | `7f21ee5` | Szortírozásra áthelyezés thumbnail-jeinek kezelése javítva; Lomtár ürítés szinkronizáció       |
| V15.8.1 | `31c576a` | Univerzális Fejléc bevezetése és SPA architektúra előkészítése                                 |
| V15.0   | `d0c9785` | Teljesítmény optimalizálás thumbnail alapú betöltéssel (Stabil V15 bázis)                      |
| V15.0   | `51d330e` | Dokumentáció: Verziótörténet frissítése a V15-ös mérföldkövekkel                               |
| V14.3   | `873c77c` | Dokumentáció: Új verziókövetési struktúra és commit táblázat bevezetése                        |
