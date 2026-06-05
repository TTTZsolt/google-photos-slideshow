# Projekt Specifikáció: Lumina Képtár (Képnézegető)

## Cél

Valóban véletlen sorrenben lejátszó Slideshow (diavetítő) és fotókezelő rendszer fejlesztése, amely a fényképek gyors válogatását is támogatja.

## Elvárások és Funkciók

1. **Zökkenőmentes Slideshow (Flicker-Free)**:
   
   - Böngészős megjelenítő (Receiver) kettős pufferelési (dual-buffer) technológiával, amely a háttérben előtölti a következő képet, megelőzve a váltások közötti villódzást vagy fekete képernyőt.
   - CSS alapú elhalványításos (`opacity cross-fade`) képváltások.

2. **Hatékony Felhő-integráció (Backblaze B2)**:
   
   - Felhőtárhelyen tárolt képeket vetít ki helyi hálózaton található kijelzőkre (pl. fali tabletek, okostévék másodlagos monitorok) anélkül, hogy a teljes képtárat le kellene tölteni a lejátszó eszközre.
   - Indexelő háttérfolyamat (`worker.py`), amely SQLite adatbázisba (`photos_app.db`) menti a felhőtárhely kép-metaadatait, elkerülve a gyakori B2 API lekérdezéseket.
   - Képbetöltés közvetlenül a B2 felhőből Cloudflare CDN proxyn keresztül a hálózati sávszélesség és költségek optimalizálásához.
   - Bélyegkép (thumbnail) támogatás a gyors betöltésért (`-thumbs` vödrök).

3. **Központi Távirányító (Dashboard)**:
   
   - Egy webes felület, ahonnan vezérelhető a vetítések indítása, megállítása (`master_switch`), a képek szinkronizálása és a mappák kijelölése.

4. **Chromecast (TV) Cast támogatás**:
   
   - `catt` (Cast All The Things) integráció, amely lehetővé teszi, hogy egyetlen gombnyomással átküldjük a slideshow-t a helyi hálózaton talált okostévékre.

5. **Digitális Képretusáló Labor**:
   
   - Menet közben a Receiver felületen megjelölhetőek (Flag) a hibás (pl. rosszul elforgatott, piros szemes) fotók.
   - A megjelölt képek a Dashboard Digitális Laborjából közvetlenül megnyithatóak a beépített webes **Photopea** képszerkesztőben, ahonnan a mentés után a javított verzió automatikusan felülírja a felhőbeli példányt, a régit pedig archiválja.

6. **Tinder-stílusú Kategória Válogató (Szortírozó)**:
   
   - Mobilbarát érintős felület, ahol ujjhúzással (Swipe) gyorsan kategóriákba sorolhatóak (Család, Utazás stb.) vagy törlésre jelölhetőek a képek.
   - **Zero-Move Architektúra**: A válogatásnál a képek nem mozognak fizikailag a felhőben, csak adatbázis bejegyzést és B2 fájl metaadatot kapnak, kivéve a Lomtárba helyezést.

7. **Lomtár és Visszavonás (Undo)**:
   
   - Biztonsági lomtár (`torles-elott` vödör) a véletlen törlések elkerülésére, és egy lépésig visszavonható (Undo) szortírozási művelet.
