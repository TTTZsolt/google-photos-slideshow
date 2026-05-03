# Lumina Képtár - Verziótörténet

Ez a dokumentum követi a Lumina projekt mérföldköveit és fejlesztési szakaszait.

## [V15.8.1] - Universal Header és Strukturális Frissítés (2026-05-03)
- **Universal Header**: Központi fejléc bevezetése minden modulhoz a tisztább átláthatóság érdekében.
- **Dinamikus Navigáció**: A fejléc automatikusan alkalmazkodik az aktív modulhoz (ikon + cím).
- **UX Finomhangolás**: Kisebb méretű branding és állandó elérhetőségű Home gomb a modulokban.
- **Premium Dark Mode**: Teljesen fekete/sötétkék téma (`slate-950`) üveghatású sötét panelekkel.

## [V15.8.0] - Moduláris Alapok (2026-05-03)
- **SPA Architektúra**: Teljes átállás Single Page Application modellre.
- **Egyedi Fejlécek**: Modulonkénti elkülönített navigáció és stílus.

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
