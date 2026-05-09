Ez a dokumentum követi a Lumina projekt mérföldköveit és fejlesztési szakaszait.
1. Kérlek minden fejlesztési lépésről készíts egy commit-ot magyarázó szöveggel.
2. Mindíg ajánlj fel egy magyarázó szöveget és legyen lehetőségem azt átfogalmazni.
3. Készíts táblázatot a commit-okról egy verzión belül: minden commitnak legyen egysora: verzió szám, commit szám és a magyarázó szöveg.
4. A commit táblázatot a Lumina Képtár Commit fejezetben helyezd el.
5. A fő verziók és magyarázatuk továbbra is a Verziótörténet fejezetben kerüljön felsorolásra.

# Lumina Képtár - Verziótörténet   

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

| Verzió | Commit | Magyarázat |
| :--- | :--- | :--- |
| V15.8.4 | `8d2c4a1` | Rendszer dokumentáció frissítése az új Zero-Move és Single-Bucket munkafolyamathoz |
| V15.8.4 | `e9f2a41` | Zero-Move Sorter architektúra és párhuzamosított B2 műveletek implementálása |
| V15.8.3 | `645e544` | Szortírozó HD Zoom támogatás nagyításkor |
| V15.8.2 | `bb26c90` | Verziószám emelése V15.8.2-re a kódban és a dokumentációban |
| V15.8.2 | `b75b1be` | Mover funkció részletes dokumentálása és szerver stabilitási javítás |
| V15.8.1 | `d6274f6` | Digitális Labor: Új retusálási mentési logika és fájlnév konvenció bevezetése |
| V15.8.1 | `7f21ee5` | Szortírozásra áthelyezés thumbnail-jeinek kezelése javítva; Lomtár ürítés szinkronizáció |
| V15.8.1 | `31c576a` | Univerzális Fejléc bevezetése és SPA architektúra előkészítése |
| V15.0 | `d0c9785` | Teljesítmény optimalizálás thumbnail alapú betöltéssel (Stabil V15 bázis) |
| V15.0 | `51d330e` | Dokumentáció: Verziótörténet frissítése a V15-ös mérföldkövekkel |
| V14.3 | `873c77c` | Dokumentáció: Új verziókövetési struktúra és commit táblázat bevezetése |
