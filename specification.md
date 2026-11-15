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
   - A Lomtár ürítése elemenként, a sikeres B2-törlés után törli az adatbázis-rekordot (tombstone-nal), és a hozzá tartozó thumbnailt is a tényleges B2 file_id alapján távolítja el.
   - A Lomtárból visszaállítás közvetlenül a fő vödörbe (`kepek02`) történik (Zero-Move).

8. **Mappa Kanban (Visszamozgató / Mover)**:
   
   - Mappaböngészőből megnyitható Kanban tábla: oszlopok a *Törlendő*, *Besorolatlan* és minden felhasználói kategória. Képek (egyesével vagy Ctrl/Shift kijelöléssel csoportosan) húzással sorolhatók át; a módosítások csak a **Változások Mentése** gombra íródnak ki (DB + B2 metaadat/mozgatás a háttérben).
   - Mappánként max. 100 kép jelenik meg, `offset` alapú lapozással (mentés után a következő adag töltődik be).
   - Nagyított képnézet: dupla kattintás; PageUp/PageDown lapozás a kategórián belül, L/R forgatás (mentéssel, valós idejű előnézettel), Delete = Törlendőbe sorolás.
   - A Mappaböngésző külön sorban mutatja az alkönyvtár nélküli, közvetlenül a mappában lévő képeket is.

9. **Kategóriák kezelése AI-leírással**:
   
   - Dinamikus kategóriák (név, ikon, szín) és kategóriánkénti **"Leírás az AI számára"** szöveg, amely beépül a Gemini promptba.
   - A kategória B2 fájl metaadatban (`X-Bz-Info-category`) is tárolódik, így a besorolás eszközfüggetlen. Ha egy kép vödre nem változik, a kategória a `B2Client.update_file_info()` hívással íródik ki.

10. **AI-alapú előszűrés és besorolás (Gemini)**:
    
    - Válogatási módok: *Manuális*, *Csak AI selejtezés*, *Teljes AI (selejt + csoportosítás)*; szűrés kategorizálatlan képekre vagy a teljes mappára.
    - Modellválasztó: alapértelmezett `gemini-3.5-flash-lite`, választható Flash / Pro Preview; a 2.5-ös és korábbi generáció kivezetve. Modellhiba esetén tisztított fallback-lánc (`FALLBACK_MODELS`), a visszaesés jelezve a felhasználónak; az AI-hibák az `ai_error` oszlopba kerülnek.
    - **Egyéni törlési szempontok**: szabadszöveges szabályok külső fájlban (`egyeni_torlesi_szempontok.txt`), kétirányú szinkronnal a felülettel.
    - **Duplikátum-előszűrés**: dHash perceptual ujjlenyomat alapú csoportosítás (sorozatfelvételek), csoportonként egyetlen több-képes Gemini-hívás dönti el a megtartandó példányt. Kameramozdulás-toleráns két-lépcsős egyezés (szigorú hash-küszöb, vagy laza küszöb + fájlnévi időbélyegek 15 mp-en belül). Csukott szemes csoportnál tie-breaker: a jobb arckifejezés nyer. Env: `DUPLICATE_HASH_THRESHOLD` (10), `DUPLICATE_HASH_LOOSE_THRESHOLD` (28), `DUPLICATE_TIME_GAP_SECONDS` (15).
    - **Teljesítmény/kvóta**: konfigurálható `GEMINI_RPM_LIMIT` (alap 12, fizetős kulccsal akár ~900) és párhuzamos feldolgozás `GEMINI_MAX_CONCURRENCY` (alap 1); közös ratelimiter, workerenként saját DB-kapcsolat.
    - Valós idejű folyamatjelző (játékos státuszfeliratokkal), menet közbeni leállítás.
    - **Jóváhagyó nézet (`/review`)**: az AI javaslatai nem mentődnek automatikusan; húzással módosíthatók, egyenként vagy tömegesen (Összes elfogadása / elvetése) elfogadhatók. Ugyanazok a nagyító-billentyűk, mint a Kanbanban (PageUp/PageDown, L/R, Delete – itt azonnali mentéssel).

11. **Slideshow szűrők és gyors kategorizálás vetítés közben**:
    
    - Indítási módok a Slideshow Setup oldalon: Shuffle All Photos, mappa/kategória szerinti vetítés, valamint általános dátumtartomány-szűrő (`date_from`/`date_to`, `YYYY-MM-DD`, a `MediaItem.creation_time` EXIF-dátum alapján) a `/api/media/random` végponton. Gyorsgombok: Utolsó hónap / hét / nap (gördülő időablak), egy kattintásra indítva.
    - A szűrő állapota átmegy az URL-en, a lekérdezéseken és a Chromecast-küldésen is; a szűrt pakli saját kulccsal rendelkezik.
    - **A `creation_time` a felvétel ideje**, nem a B2 feltöltési idő: a szinkron az útvonalból (`ÉÉÉÉ/HH/[NN-album/]fájlnév`) és a fájlnévből számolja (`backend/utils/media_dates.py`, helyi idő). Ha az útvonal és a fájlnév ellentmond, az útvonal az irányadó. A már tárolt, az útvonallal összeegyező pontos időt (pl. a telefonos feldolgozó EXIF-értékét) a szinkron megtartja. Ahol a dátum nem állapítható meg, az érték `NULL`, és a kép kimarad a dátumszűrt vetítésből. A pontosság a friss, telefonról érkező képeknél számít; a régi (Takeout) képek eleve kívül esnek az „utolsó hónap/hét/nap" ablakon.
    - Kompakt, mobilbarát Setup felület (Idő (s), Nevek és Kategória kapcsolók, 2×2 rács telefonon).
    - **Gyors kategorizálás**: a Flag gomb melletti ikonra felugró kategórialista (a „Törlés (AI)" rendszerkategória nélkül); a besorolás a `/api/classification/bulk-classify-manual` végponton azonnal mentődik.

12. **Automatikus fényképfeltöltés Androidról (FolderSync + `beerkezo` vödör)**:
    
    - A telefon kamera-mappáját a Play Áruházas FolderSync S3-kompatibilis szinkron-app tölti fel a dedikált `beerkezo` B2-vödörbe (Termux/SSH nem szükséges).
    - A backend (`backend/incoming_processor.py`) 5 percenként, vagy a `POST /api/incoming/process-now` hívásra feldolgozza a vödröt: SHA1 alapú dedup/tombstone-ellenőrzés, EXIF-dátum szerinti Év/Hónap útvonal, bélyegkép-generálás, feltöltés a `kepek02`-be és DB-rekord létrehozása.
    - Újra-feltöltés elleni védelem: a feldolgozott fájl helyére azonos nevű 0 bájtos helyjelölő kerül.
    - `GET /api/media/check-sha1/{sha1}`: megmondja, hogy a tartalom már fent van-e, vagy korábban tudatosan törölték (tombstone).

13. **Üzembiztos B2-szinkron és thumbnail-kezelés**:
    
    - A teljes B2-szinkron a bulk-listázásból hiányzó fájlt csak célzott, külön megerősítés után törli a DB-ből (a B2 eshetőleges konzisztenciája miatti adatvesztés ellen); a fájlnevenkénti B2-verzióváltást duplikáció nélkül kezeli.
    - A háttér-B2 műveletek (`b2_move_background_task`) 3× újrapróbálkoznak (2/4/8 mp).
    - Minden teljes szinkron végén önjavító lépés (`thumb_worker.generate_missing_thumbnails`, minden vödörre, a Lomtárral együtt) újragenerálja a hiányzó thumbnaileket.
    - Szortírozó: HD zoom (nagyításkor eredeti felbontás), könyvtárankénti ABC-sorrend, Pánik gomb a várólista ürítésére, concurrency lock a duplikált képek ellen.
14-  Szeretném kiegészíteni a képnézegetőt egy video nézegetővel is. Mit javasolsz, hogyan valósítsam meg
    1- Itt is szeretnék olyan szétválasztást, mint a képeknél: család, utazás, siklóernyő, állatok csoportosítást
       
    2- Kellene egy felület, ahol "előképek" és a videók megnevezései alapján ki tudom választani, hogy mit szeretnék megnézni
       
    3- Azt is szeretném, hogy a képnézegető futása esetén a videók lejátszása ugyanolyan véletlenszerűen történjen, mintha kép lenne. 
    4- Kérdések-válaszok
    5- 1. **Mennyi és milyen videó van?** Hány db, összesen hány GB, mi a jellemző formátum? A telefonok HEVC/H.265-öt vesznek fel, amit a tablet böngészője vagy a Chromecast nem biztos, hogy lejátszik. Ez dönti el, kell-e átkódolás.
          1. Jellemzően MOV és mp4 videók
          2. Most szeretnék majd elkezdeni VHS videókat digitalizálni, majd azokat is szeretném felrakni
       2. **Hol vannak most a videók?** A Takeout-exportban, a telefonon (a FolderSync a `beerkezo`-ba már viszi őket?), vagy már a B2-ben? Mindkét útvonalat kezeljem?
          1. Jellemzően a Takaout exportban. át kell alakítani a Fénykép előkészítés és B2 feltöltés szolgáltatást, hogy a video-k is menjenek fel a Takeout-ból a B2-be a képekkel azonos módon
       3. **Fut-e `ffmpeg` a tableten** (Termux, `pkg install ffmpeg`)? A poszterkép-generálás és az `ffprobe` ezen múlik. Ha nem megy, a poszterképet a PC-n is lehet generálni.
          1. Nem tudom, hogy fut-e
       4. **Hang vetítés közben:** legyen alapból néma (hogy ne ütközzön a `music.py` YouTube-zenéjével), vagy hanggal menjen, és a zene halkuljon el?
          1. Hanggal kellene mennie, youtube elhalkítás mellett
       5. **Vegyes vetítés:** a videó teljes hosszában menjen, vagy legyen maximum (pl. 30–60 mp)? Mi legyen az alapértelmezett videó-arány? 
          1. 60 mp fusson le
          2. 10 képre essen 1 video
       6. **Cím:** a „megnevezés" a fájlnév (pl. `VID_20240713_...`) vagy a mappa-caption, esetleg te nevezed el kézzel (`title`)? Ha kézzel, kell-e tömeges átnevezés?
          1. Mappa caption, de kellene valami megjegyzés lehetőségét hozzátenni a video-khoz
       7. **Költség és Cloudflare:** a videó sávszélessége a B2 letöltési díját növeli. A Cloudflare ingyenes csomagjának szolgáltatási feltételei korlátozhatják a nagy videók proxyzását. Ezt a döntés előtt pontosan ellenőrizni kell. Ha gond, a videók közvetlenül a B2-ről mennének, proxy nélkül. Van elképzelésed a mennyiségre?
          1. Végeztem egy számítást 1 TB-re és az lett a döntés, hogy B2-t használok
       8. **Külön oldal vagy a Dashboardba integrálva?** A Videótár legyen önálló `/videos` oldal, vagy a Szortírozóhoz hasonló modul a Dashboardon?
          1. Modul a dashboard-on
