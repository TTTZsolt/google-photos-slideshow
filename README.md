# Lumina Képtár (V16.3.4)

**Cél**: Fényképek szortírozása nyomógombokkal


This project is a high-performance, web-based random photo slideshow that pulls images from Backblaze B2. It is designed to be flicker-free and works on any device with a modern web browser.

## Key Features

### 1. Flicker-Free Transitions
- Uses a dual-buffer strategy in the browser.
- Smooth CSS `opacity` transitions (cross-fade).
- Background preloading of the next image to eliminate loading gaps.

### 2. B2 API Optimization
- **Client Reuse**: Dramatically reduces authorization calls to Backblaze.
- **Token Caching**: Caches download authorization tokens for 2 hours.
- **Improved Reliability**: Fixes "transaction cap exceeded" errors even with fast image switching.

### 3. Customizable Filename Display
- Optional filename overlay at the bottom of the screen.
- Toggleable directly from the Dashboard.
- Clean, semi-transparent badge design for maximum readability.

### 4. Simplified Web Dashboard
- Easy management of B2 bucket connections.
- Global start/stop controls.
- Adjustable slideshow interval.
- Direct link to the Slideshow Receiver.

### 5. Immersive UI & Smart Sorting (V14.0)
- **Full-Screen Sorting**: Immersive, distraction-free environment for photo classification with floating transparent controls.
- **Smart Undo (Visszavonás)**: Immediate recovery of the last classification or deletion with a simple click and server-side revert.
- **Trash Preview**: High-resolution, full-screen inspection of the trash bin before final deletion.
- **Adaptive UX**: Intelligent notifications that learn from usage to become less intrusive over time.

## How to use

1.  **Requirement**: Run all commands from the project root directory:
    `C:\Users\zsolt.tuske\.gemini\antigravity\playground\swift-newton\`

2.  **Installation**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the server**:
    ```bash
    python -m backend.main
    ```
3.  **Configure**:
    - Open `http://localhost:8080`.
    - Connect your Backblaze B2 bucket (Key ID, Application Key, Bucket Name).
    - Click "Resync" to index your photos.
4.  **Run Slideshow**:
    - Click "Start" on the Dashboard.
    - Click the "Open Slideshow Receiver" link or open `http://<your-ip>:8080/receiver` on any device.

## Mover Funkció - Zero-Move Architektúra (V15.8.4)

A rendszer a válogatási folyamat gyorsítása érdekében immár **Zero-Move** logikát használ:

*   **Válogatás előkészítése (Bulk Reverse)**: A képek **nem mozognak fizikailag** a vödrök között. A rendszer csak megjelöli őket válogatásra az adatbázisban. Ez 1300+ kép esetén is azonnali eredményt ad.
*   **Klasszifikáció**: Ha a kép már a `kepek02` (aktív) vödörben van, a mentéskor nem történik fájlmozgatás, csak a metaadatok frissülnek a felhőben.
*   **Törlés (Trash)**: Fizikai mozgatás csak törléskor történik (`kepek02` -> `torles-elott`), amit párhuzamosított szálakon végzünk a maximális sebességért.
*   **Visszaállítás (Lomtárból)**: közvetlenül `torles-elott` -> `kepek02`, nem a `forras`-on keresztül (2026-08-18-tól).
*   **Egyszerűsített struktúra**: Minden kép a `kepek02` vödörben lakik. A `forras` vödörnek 2026-08-18 óta gyakorlatilag **nincs aktív szerepe** a rendszerben (sem a Mover, sem a Lomtár-visszaállítás nem használja) — csak a régi, `upload_with_thumbs.py`-alapú feltöltési út igényli, ha valaki azt választja.


## Versions
- **V14.3**: Teljes verzió egységesítés és elmaradt dokumentációs javítások.
- **V14.2**: 2026-05-02-i stabil verzió (Robusztus szinkronizáció + ékezet-érzéketlen keresés).
- **V14.0**: Full screen Szortírozó + undo megvalósítása.
- **V13.8**: Több felhasználós működés javítása.
- **V13.7**: Stabil verzió, UI egységesítés előtt, HTML sablonnal.
- **V13.5**: Felhő-szintű metaadatok (B2 Info category), központi osztályozás szinkronizációja.
- **V13.0**: Moduláris Dashboard architektúra (SPA), aszinkron adathozzáférés és navigáció.
- **V12.0**: Interaktív Receiver vezérlés (Következő gomb), Cloudflare Proxy V2 integráció.
- **V11.0**: Dinamikus Kategória Kezelő (egyedi ikonok, színek és nevek).
- **V10.0**: Fotó Szortírozó (Classifier) gombokkal.
- **V9.0**: Szortírozó: swipe stílusú.
- **V8.3**: Stabil alapverzió (Fő verzió). Catt timeout kezelés és hálózati stabilitás.
- **V8.2**: Screen Wake Lock implementáció (kijelző elsötétedés elleni védelem).
- **V8.1**: UI refinements and minor fixes.
- **V8.0**: receiver default interval 240s, minor UI alignment/refinements.
- **V7.9**: Digitális Labor (Retouch Queue), UI button alignment.
- **V3.1**: GoogleCast integration via `catt`, Consolidated UI, Dynamic Settings.
- **V3.0**: Stable release (Optimized B2, Web-based, Flicker-free).
- **v1.0**: Legacy version for direct Chromecast casting (deprecated).

