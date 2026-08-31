Ez a dokumentum követi a Lumina projekt mérföldköveit és fejlesztési szakaszait.

1. Kérlek minden fejlesztési lépésről készíts egy commit-ot magyarázó szöveggel.
2. Mindíg ajánlj fel egy magyarázó szöveget és legyen lehetőségem azt átfogalmazni.
3. Készíts táblázatot a commit-okról egy verzión belül: minden commitnak legyen egysora: verzió szám, commit szám és a magyarázó szöveg.
4. A commit táblázatot a Lumina Képtár Commit fejezetben helyezd el.
5. A fő verziók és magyarázatuk továbbra is a Verziótörténet fejezetben kerüljön felsorolásra.

# Lumina Képtár - Verziótörténet

## [V16.3.6] - Lomtár-ürítés thumbnail-fix (2026-08-31)

- **Fix: árva thumbnailek a Lomtár-ürítés után**: a fő fájl törlése után a hozzá tartozó thumbnailt egy üresen hagyott (`""`) file_id-vel próbálta törölni a kód - a B2 API ezt mindig elutasította, a csupasz `except: pass` pedig csendben elnyelte a hibát. Emiatt minden eddigi Lomtár-ürítésnél a fő fájlok töröltek, de a thumbnailek örökre a `*-thumbs` vödörben maradtak (kb. 1060 db, ~1.45 GiB felesleges tárhely, most eltakarítva). Javítva: a thumbnail törlése előtt a tényleges B2 file_id-t név alapján kérjük le, azzal törlünk.
- **Megjegyzés**: az AI-osztályozás (Mover) jelenleg **Gemini 2.5 Flash** modellel fut (`backend/utils/ai_service.py` alapértelmezett modellje és az UI modell-választó alapértéke).

## [V16.3.5] - Duplikátum-előszűrés a Mover AI-osztályozásához (2026-08-30)

- **Duplikátum-felismerés**: a Mover AI-folyamata eddig minden képet külön-külön küldött a Gemini-nek, így sosem látott egyszerre két képet - nem tudta érvényesíteni az `egyeni_torlesi_szempontok.txt` "ha több nagyon hasonló kép van, csak egyet tarts meg" szabályát. Új előszűrő lépés: olcsó dHash (difference-hash) perceptual ujjlenyomat minden képhez, majd az egymás után következő, nagyon hasonló képek (pl. sorozatfelvételek) csoportosítása, majd csoportonként EGYETLEN több-képes Gemini-hívás dönti el, melyik példányt érdemes megtartani.
- **Kameramozdulás-toleráns egyezés**: a dHash nem eltolás-toleráns - egy kis kameramozdulás két felvétel között (pl. állókép egy szoborról) nagy hamming-távolságot okozhat, holott a képek valójában ugyanaz a felvétel. Két-lépcsős egyezés: a szigorú küszöb felett is elfogad egy lazább hash-egyezést, de csak ha mindkét fájlnévből kiolvasható egy nagyon közeli (alapértelmezett: 15 másodpercen belüli) időbélyeg is - így a fellazított küszöb nem növeli meg a téves, távoli fényképek összemosásának kockázatát. Új env-változók: `DUPLICATE_HASH_THRESHOLD` (10), `DUPLICATE_HASH_LOOSE_THRESHOLD` (28), `DUPLICATE_TIME_GAP_SECONDS` (15).
- **Csukott szem tie-breaker**: ha egy duplikátum-csoport MINDEN tagján csukva van a szem, a Gemini-prompt mostantól explicit tartalék-szempontot kap: ilyenkor a jobb arckifejezésűt/mosolygósat válassza, ne véletlenszerűen döntsön.
- **Jópofa várakozó animáció**: a Mover AI-folyamat haladásjelzője pörgő pontsort és véletlenszerűen váltakozó, játékos "mit csinál épp az AI" feliratokat kapott, hogy várakozás közben ne legyen türelmetlen a felhasználó.
- **Fix: hiányzó `B2Client.update_file_info()`**: a kategória-jóváhagyás azon ága, amikor egy kép vödre nem változik (csak kategóriát kap), egy sosem létezett metódust hívott, ezért a kategória eddig kizárólag a helyi SQLite adatbázisban létezett, a B2 fájl `file_info`-jába sosem íródott ki. A hiányzó metódus pótolva (a meglévő `move_file()`-ra épül, azonos forrás- és célvödörrel); a tesztelés során jóváhagyott 316 kategória utólag visszapótolva a B2-n.

## [V16.3.4] - Slideshow UI finomhangolás + gyors kategorizáló gomb vetítés közben (2026-08-25)

- **Slideshow Setup gyorsgombok**: a "Fényidő" fény-spektrum sáv (V16.3.3 kreatív első próbálkozása) helyett egy egyszerűbb, kompakt megoldás - a Shuffle All Photos alatt Hó/Hét/Nap felirat + zöld lejátszás-ikon + a feloldott dátum, egy kattintásra azonnal indítva, külön megerősítő lépés nélkül.
- **Setup felület egyszerűsítése**: "Idő (s)" egyértelmű felirat (a redundáns "s" jelzés törölve), a "Nevek" kapcsoló alapértelmezetten bekapcsolva, a "Név" (device name) mező eltávolítva a felületről (a funkció a háttérben megmaradt, csak kézzel már nem állítható be itt).
- **Mobil footer javítások**: a beállítások alsó sora telefonon 2×2 rácsba rendezve (Idő+Kategória felül, Nevek+Kateg. kapcsoló alul), `md` töréspontig, hogy köztes szélességű telefonok se csússzanak át a deszktop flex-sorba; deszktopon (md+) az eredeti sorrend és egyenletes elosztás megmaradt. A Setup modal `max-height`-je `80vh` mellett `80dvh`-t is kap, hogy a mobil böngésző címsávja miatt ne vágódjon le az alsó sor.
- **Új funkció - gyors kategorizálás vetítés közben**: "Kategorizálás" ikon a Flag gomb mellett - rákattintva egy felugró listázza a kategóriákat (a "Törlés (AI)" rendszerkategória nélkül), kiválasztásra azonnal elmenti a besorolást a meglévő `/api/classification/bulk-classify-manual` végponton keresztül, ugyanazzal a mechanizmussal, mint a kézi Kanban.

## [V16.3.3] - Általános dátumtartomány-szűrő a Slideshow-hoz (2026-08-24)

- A V16.3.1-es, kizárólag "utolsó hónapra" szabott szűrőt (`last_month` bool) felváltotta egy általános `(date_from, date_to)` 'YYYY-MM-DD' dátumtartomány-mechanizmus a `get_random_image`-ben és a `/api/media/random` végponton, `MediaItem.creation_time` alapján szűrve.
- Frontend: három gyorsgomb (Utolsó hónap/hét/nap) tölti ki a dátumokat a megfelelő gördülő időablakkal - ez a `verziokontroll.md`-ben nem külön dokumentált, kísérleti UI-verzió (fénysáv, kézi "Tól-Ig" dátumválasztó) volt a V16.3.4 véglegesített, kompaktabb megoldásának előzménye.

## [V16.3.2] - Fizetős Gemini kulcs, párhuzamos AI-osztályozás, Jóváhagyó billentyűparancsok (2026-08-23)

- **Biztonsági javítás**: a `.env.txt` fájl (egy régi, nyilvánosan kiszivárgott Gemini API kulcsot tartalmazó, véletlenül git-követett fájl) eltávolítva a git követésből, `.gitignore` kiegészítve (`.env.*`). A kiszivárgott kulcs visszavonva a Google AI Studio-ban; a ténylegesen használt kulcs (a helyesen `.gitignore`-olt `.env`-ben) sosem volt kitéve.
- **Fizetős Gemini tier**: a Lumina AI-osztályozáshoz használt Google Cloud projekten (billing bekapcsolva, Tier 1) mostantól sokkal magasabb (1000 RPM `gemini-2.5-flash`-nél) a kvóta az ingyenes tier (12 RPM) helyett.
- **Konfigurálható RPM-limit**: a képenkénti mesterséges várakozás a `GEMINI_RPM_LIMIT` környezeti változóból számolódik (alapértelmezett: 12, tehát változatlan marad, amíg be nem állítják) - fizetős kulcshoz magasabb értékkel (pl. 900) gyakorlatilag elhanyagolható a várakozás.
- **Párhuzamos AI-feldolgozás**: a `GEMINI_MAX_CONCURRENCY` változóval szabályozható, hány kép menjen egyszerre a Gemini-nek (alapértelmezett: 1 = szekvenciális, változatlan viselkedés). Minden egyidejű worker saját adatbázis-kapcsolatot nyit (a meglévő B2-háttérszál mintát követve), egy megosztott ratelimiterrel, hogy összesen se lépjék túl a beállított RPM-et.
- **Jóváhagyó nézet (`/review`) billentyűparancsai**: a képnagyító modálban mostantól ugyanaz a billentyűkészlet érhető el, mint a kézi Kanban-nál - PageUp/PageDown lapozás a kategórián belüli képek között, L/R forgatás, Delete a Törlendő oszlopba helyezés (itt azonnali mentéssel, mivel a Jóváhagyó nézetnek nincs külön Mentés lépése).

## [V16.3.1] - "Pictures of Last Month" gomb a Slideshow-hoz (2026-08-23)

- **Új Slideshow indítási mód**: a Slideshow Setup oldalon (Shuffle All Photos gomb alatt) egy új, "Pictures of Last Month" gomb indítja el a vetítést, ami kizárólag az utolsó 30 nap (gördülő időablak, nem naptári hónap) fényképeit játssza le véletlenszerű sorrendben.
- **Backend**: a `/api/media/random` végpont és a `SlideshowController.get_random_image` egy új `last_month` paramétert fogad, ami a `MediaItem.creation_time` (EXIF-dátum) alapján szűr; a szűrt paklinak (deck) saját kulcsa van, hogy ne keveredjen a mappa/kategória szerinti válogatással.
- **Konzisztencia**: a szűrő állapota átmegy az URL-en (megosztás/újratöltés), a lekérdezéseken és a Chromecast-küldésen (`initiateCast`) is.

## [V16.3.0] - Android automatikus feltöltés újratervezése: FolderSync + beérkező vödör (2026-08-19)

- **A V16.2.2-es Termux-alapú megoldás teljes leváltása**: a korábbi, saját `inotify`-figyelő szkriptre és SSH-hozzáférésre épülő megoldás telepítése/karbantartása túl bonyolult lett volna egy nem technikai felhasználó számára, ha ez egyszer termékké válna. Helyette a telefon oldalán mostantól egy kész, Play Áruház-os S3-kompatibilis szinkron-app (**FolderSync**) elég — nincs Termux, nincs SSH, nincs csomagtelepítés a telefonon.
- **Új, dedikált B2-vödör (`beerkezo`)**: a FolderSync ide szinkronizálja a telefon kamera-mappáját, eredeti fájlnévvel, feldolgozás nélkül.
- **Új szerver-oldali automatikus feldolgozó** (`backend/incoming_processor.py`): a Lumina backend 5 percenként (vagy a `POST /api/incoming/process-now` végponttal azonnal) átnézi a `beerkezo` vödröt, SHA1 alapján dedup/tombstone-ellenőrzést végez, EXIF-dátum alapján Év/Hónap útvonalra rendez, bélyegképet generál, és feltölti a `kepek02`-be az adatbázis-rekord közvetlen létrehozásával.
- **Végtelen újra-feltöltés elleni védelem**: feldolgozás után az eredeti fájlt a `beerkezo`-ban nem töröljük teljesen, hanem egy azonos nevű, 0 bájtos helyjelölőre cseréljük — a FolderSync (méret-ellenőrzés nélkül beállítva) így "már szinkronizált"-nak látja, és nem tölti fel újra minden alkalommal ugyanazt a képet.
- **Hibafeltárás és javítás (élő tesztelés közben)**: kiderült, hogy a régi Termux-folyamat a telefonon a háttérben (Termux:Boot-tal) továbbra is futott, és versenyhelyzetben volt az új FolderSync-megoldással - a saját (elavult) logikájával "elnyelte" az új fotókat, mielőtt a FolderSync szinkronizálhatta volna őket. Megoldás: a telefonon leállítottuk a futó folyamatot, töröltük a Termux:Boot indítószkriptjét és a `~/lumina_auto_feltoltes/` mappát, valamint a `beerkezo` vödörből a régi megoldás maradvány-fájljait (`feltoltve/` mappa, `feltoltott_kepek.csv`, minden verzióval együtt).
- **Dokumentáció**: a régi Termux-alapú útmutatók és szkriptek (`android_auto_feltoltes/`) törölve, az `Automatikus fényképfeltöltés.md` tervezési jegyzet és a `folder_sync_setup_utmutato.md` frissítve az új architektúrának megfelelően, kiegészítve a FolderSync két mappapárjának (kamera-mappa + kézi/régebbi képek) szükséges beállításaival (fájlméret-ellenőrzés kikapcsolása, szinkron utáni törlés).
- **Éles teszt eredménye**: több körben, valódi fotókkal tesztelve - egyaránt automatikusan (a szerver 5 perces időzítője által elkapva) és kézzel kiváltva -, a régi Termux-folyamat eltávolítása után a versenyhelyzet megszűnt, minden szinkronizált fájl helyesen célba ért a `kepek02`-ben, a duplikátum-szűrés (SHA1) is helyesen működött.

## [V16.2.2] - Android automatikus fényképfeltöltés (2026-08-18)

- **Új eszköz** (`android_auto_feltoltes/`): Termux + `inotify-tools` alapú háttérfolyamat a telefonon, ami a kamera-mappát figyeli, és minden új fotót közvetlenül a `Kepek02` vödörbe tölt fel (EXIF-dátum alapú Év/Hónap struktúra), be/kikapcsolható jelzőfájllal.
- **Automatikus adatbázis-szinkron**: sikeres feltöltés után a script meghívja a mindig futó (tablet) példány `/b2/sync/{id}` végpontját, hogy a kép azonnal megjelenjen a Luminában, kézi Sync nélkül.
- **Kézi feltöltés natív Galéria-kiválasztással**: a telefon saját, bélyegképes, többes kijelöléses Galéria/Fotók felületéből "Megosztás → Mentés ide" művelettel egy `Pictures/LuminaFeltoltes` mappába helyezett képeket a figyelő szintén automatikusan feltölti (a be/kikapcsolt állapottól függetlenül) — erre való, ha egy kép az automatikus feltöltés kikapcsolt állapotában készült.
- **Új backend végpont**: `GET /api/media/check-sha1/{sha1}` — megmondja, hogy egy tartalom SHA1 alapján már fent van-e a fő bucketben, vagy korábban tudatosan törölve lett-e (tombstone). A telefonos feltöltő minden kép előtt ezt ellenőrzi, hogy elkerülje a duplikált feltöltést és a szándékosan törölt tartalom véletlen visszaállítását — ugyanaz a védelem, mint a Takeout-feltöltő eszköznél.
- **Naplózás**: a kézi feltöltésnél feldolgozott képek nem másolódnak fizikailag sehova (törlődnek a telefonról sikeres feltöltés után) — csak egy `feltoltott_kepek.csv` napló őrzi az időpontot, fájlnevet és a kimenetel státuszát (`feltoltve` / `skip-mar-fent` / `skip-torolve`).

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
| V16.3.6 | `aa52196` | Fix: Lomtár-ürítésnél a thumbnail törlés üres file_id-vel próbálkozott, sosem sikerült - a törölt képek thumbnailje örökre a *-thumbs vödörben maradt |
| V16.3.5 | `a346a45` | Fix: hiányzó B2Client.update_file_info() pótlása (kategória-jóváhagyás nem íródott ki a B2-re) |
| V16.3.5 | `bbeb15e` | Duplikátum-előszűrés pontosítása (kameramozdulás-toleráns egyezés) + tie-breaker + várakozó animáció |
| V16.3.5 | `fc35472` | Duplikátum-előszűrés a Mover AI-osztályozásához: perceptual-hash csoportosítás + több-képes AI-döntés |
| V16.3.4 | `8b46516` | Slideshow UI finomhangolás (Hó/Hét/Nap gyorsgombok, mobil footer) + gyors kategorizáló gomb     |
| V16.3.3 | `64d1627` | Általános dátumtartomány-szűrő a Slideshow-hoz (Utolsó hónap/hét/nap + kézi dátumok)            |
| V16.3.2 | `95c2834` | Párhuzamos AI-osztályozás (GEMINI_MAX_CONCURRENCY) + Kanban billentyűparancsok a Jóváhagyóban   |
| V16.3.2 | `f86bbd0` | Konfigurálható Gemini RPM limit (GEMINI_RPM_LIMIT) fizetős API kulcsokhoz                       |
| V16.3.2 | `625ba0a` | Biztonsági javítás: .env.txt eltávolítása a git követésből (kiszivárgott Gemini kulcs)          |
| V16.3.1 | `d045c65` | "Pictures of Last Month" gomb a Slideshow-hoz - utolsó 30 nap véletlenszerű lejátszása          |
| V16.2.1 | `0beeea7` | Dokumentáció frissítése: forras vödör szerepének pontosítása (DOKUMENTACIO.md, README.md)     |
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
