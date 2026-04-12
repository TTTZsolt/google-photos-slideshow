# Lumina Képtár - Verziótörténet

Ez a dokumentum követi a Lumina projekt mérföldköveit és fejlesztési szakaszait.

## [V14.0] - Immerzív Szortírozó és Undo Rendszer (2026-04-12)

A V14.0 fókuszában a felhasználói élmény és a sebesség áll, különösen a nagy mennyiségű kép feldolgozása során.

### Újdonságok
- **Full Screen Szortírozó**: Teljes kijelzős, zavaró tényezőktől mentes mód a fotók átnézéséhez. Helytakarékos, áttetsző ikonok a képernyő alján.
- **Undo (Visszavonás) Funkció**: Az utolsó osztályozási vagy törlési művelet azonnal visszavonható a kis előnézeti képre kattintva. Swapping animációval és szerveroldali B2 visszamozgatással.
- **Lomtár Teljes Képernyős Előnézet**: A törlésre jelölt képek ellenőrzése nagy méretben a végleges ürítés előtt (Esc billentyű támogatás).
- **Adaptív Értesítési Rendszer**: Tanuló figyelmeztetések, amelyek többszöri használat után automatikusan átváltanak egy diszkrétebb, kompakt formátumra.
- **Standardizált Verziókezelés**: Minden rendszermodul (Dashboard, Classify, Trash, Backend) egységesített V14.0 verziójelzéssel.

---

## [V13.8] - Felhő-szintű Metaadatok (2026-04-10)
- **B2 File Info Integráció**: A kategóriák rögzítése közvetlenül a B2 fájlok metaadataiba (`category`).
- **Device-Independent Sync**: A szortírozás eredménye automatikusan szinkronizálható bármely új telepítéssel.
- **Adat Migráció**: Szkript a helyi adatbázis tartalmának felhőbe történő mozgatásához.

---

## [V13.0] - Moduláris Dashboard (2026-04-09)
- Új, kártya alapú vezérlőpult.
- Chromecast/TV támogatás integrációja.
- Digitális Labor (Photopea) és szinkronizált szerkesztés.

---
*A korábbi verziók (V1.0 - V12.0) a Git tagek között érhetőek el.*
