# Felhasználói Útmutató: Lumina Képtár (Képnézegető)

## Gyors Áttekintés
A Lumina Képtár egy Backblaze B2 felhőalapú diavetítő rendszer, amely zökkenőmentes képváltásokkal jeleníti meg a fotóidat kijelzőkön (pl. tévén, tableten), és lehetőséget biztosít a képek menet közbeni megjelölésére, Photopea-val történő retusálására, valamint mobilról történő Tinder-stílusú szortírozására.

A backend szerver jellemzően a helyi hálózati **Tableten** fut (Linux/Termux környezetben), és a Windows számítógépről indító batch fájlokkal vezérelhető.

## Használati Útmutató (Lépésről lépésre)

1. **Előfeltételek**:
   - Python 3.x és a szükséges csomagok (`requirements.txt`) telepítése.
   - Megfelelő Backblaze B2 hozzáférés konfiguráció.
   - Csatlakozás a helyi hálózathoz (TV, Tablet és PC ugyanazon a Wi-Fi-n legyen).

2. **A Szerver Indítása**:
   - Futtasd a Windows PC-den található **`tablet_start_kepnezegeto.bat`** (vagy `start_tablet.bat`) parancsfájlt.
   - Ez SSH-n keresztül elindítja a FastAPI szervert a tableten, és megnyitja neked a böngészőben a Dashboardot (Vezérlőpultot).
   - Leállításhoz futtasd a `tablet_stop_kepnezegeto.bat` fájlt.

3. **Vetítés indítása (Receiver)**:
   - Nyisd meg a megjelenítő eszközön (fali tablet, másodlagos kijelző) a következő címet (feltételezve, hogy a tablet szerver IP-je `192.168.1.157`):
     `http://192.168.1.157:8080/receiver`
   - A képváltási időt az URL paraméterben írhatod felül, pl. 2 percre: `/receiver?interval=120`.

4. **Tévére küldés (Chromecast/Google TV)**:
   - A Dashboardon görgess le a Chromecast szekcióhoz.
   - Válaszd ki a felismert tévét (pl. *Nappali TV*), és kattints a **Cast** gombra.
   - A vetítés leállításához kattints a **Stop Cast** gombra.

5. **Hibás képek megjelölése és javítása (Labor)**:
   - **Megjelölés**: Ha vetítés közben hibás fotót látsz, kattints a kijelző sarkában lévő **Zászló (Megjelölés)** ikonra. A kép piros keretet kap és bekerül a javítandó sorba.
   - **Javítás**: Ülj le a PC elé, nyisd meg a Dashboard alján lévő **Digitális Labor (Retouch Queue)** panelt. Kattints a kép melletti **Photopea** ikonra. Végezd el a forgatást/javítást a megnyíló képszerkesztőben, majd válaszd a **File -> Save** menüpontot. A javított kép visszakerül a felhőbe, a régi pedig archiválódik.

6. **Kategóriák kezelése és leírás az AI számára**:
   - **Megnyitás**: A Dashboard főoldalán kattints a **"Tags"** (címke ikonos) menüpontra — ez nyitja meg a **Kategóriák Kezelése** oldalt.
   - **Új kategória**: az "Új Kategória" gombbal hozhatsz létre egyet: megjelenített név (pl. "Család"), ikon, szín, és egy **"Leírás az AI számára"** szövegmező.
   - **Meglévő szerkesztése**: minden kategória mellett van egy ceruza ("Szerkesztés") gomb, amivel bármikor módosíthatod a nevét, ikonját, színét vagy leírását.
   - **Miért érdemes kitölteni a leírást**: ez a szöveg közvetlenül bekerül az AI-nak küldött promptba minden egyes kép besorolásakor (l. 9. pont) — tehát ha pontosan leírod, milyen jellegű képek tartozzanak egy-egy kategóriába (pl. Utazás: "külföldi és belföldi nyaralások, repülőtér, szálloda, látványosságok"; Siklóernyő: "siklóernyős felszállás, repülés közbeni felvételek, leszállóhely"), az AI érdemben pontosabban fog besorolni — anélkül, hogy a rendszernek bármi mást kellene tenned. Üresen hagyva a kategória csak a nevéből próbál "kitalálni".

7. **Fotók válogatása (Szortírozó)**:
   - Nyisd meg a Dashboardról (lehetőleg telefonon/tableten) a **Szortírozót**.
   - Egyszerre egy kép jelenik meg nagyban; a jobb alsó sarokban egy kis előnézetben látszik az előzőleg besorolt kép.
   - **Besorolás**: koppints a kép alatt megjelenő kategória-gombok egyikére (ezek a nálad definiált kategóriák, saját ikonnal és színnel) — a kép azonnal átkerül a megfelelő csoportba, és betöltődik a következő.
   - **Törlés**: koppints a bal alsó **Törlés** gombra — a kép a Lomtárba kerül.
   - **Visszavonás (Undo)**: koppints a jobb alsó sarokban látható kis előnézeti képre (ez mindig az utoljára besorolt kép) — ezzel visszavonod az utolsó döntést, és a kép újra a várólista elejére kerül.
   - **Nagyítás**: két ujjal csippentve (pinch-to-zoom) nagyíthatod és mozgathatod az aktuális képet alaposabb megtekintéshez. Noteszgépen, érintőképernyő nélkül is elérhető: **Ctrl + görgetés** vagy trackpad-csippentés a nagyításhoz, bal egérgombbal húzva pedig mozgathatod a nagyított képet.
   - **Teljes képernyő**: a jobb felső maximalizáló ikonnal válthatsz zavartalan, teljes képernyős módra.
   - **Szortírozó ürítése**: a jobb felső körkörös nyíl ikonnal kiürítheted a várólistát (a képek megmaradnak, csak a "szortírozandó" jelölés törlődik).

8. **Képek manuális "huzogatással" történő csoportosítása (Mappa Kanban)**:
   - **Megnyitás**: A Dashboardon nyisd meg a **Visszamozgató (Mover)** modult, a jobb oldali Mappaböngészőben navigálj a kívánt mappához, majd kattints a mappa neve melletti kis mappa-ikonra ("Képek megnyitása a Kanban nézetben"). Ez megnyitja az adott mappa képeit a Kanban nézetben.
   - **Oszlopok**: A tábla oszlopai balról jobbra: **Törlendő**, **Besorolatlan**, majd egy-egy oszlop minden nálad definiált kategóriának (pl. Család, Utazás, stb.).
   - **Húzás**: Fogd meg egérrel (vagy érintéssel) egy kép kártyáját, és húzd át a kívánt oszlopba. A kép azonnal átkerül a felületen, de **még nincs elmentve** — a módosított képeken egy apró sárga pötty jelenik meg.
   - **Több kép egyszerre**: Kattintással jelölj ki képeket (Ctrl+kattintás: hozzáadás a kijelöléshez; Shift+kattintás: tartomány kijelölése ugyanazon oszlopon belül), majd húzd el bármelyik kijelölt kártyát — az összes kijelölt kép együtt mozog át az új oszlopba.
   - **Nagyítás**: Dupla kattintással megnyithatod a kép nagyméretű előnézetét.
   - **Mentés**: Ha végeztél a rendezéssel, kattints a **Változások Mentése** gombra. Csak ekkor íródnak a módosítások az adatbázisba, és csak ekkor mozognak a fájlok ténylegesen a Backblaze B2-ben (a háttérben).
   - **Korlát**: Egy mappában egyszerre legfeljebb 100 kép jelenik meg (teljesítmény miatt). Ha ennél több van, egy figyelmeztető sáv jelzi ezt, és mentés után automatikusan betöltődik a következő adag.

9. **AI-alapú előszűrés és -előkészítés**:
   - **Indítás**: Ugyanabban a **Visszamozgató (Mover)** modulban, a bal oldali panelen:
     - **Szűrés kategóriára**: eldöntheted, hogy csak a még kategorizálatlan képeket vonja be a folyamat, vagy az adott mappa/kategória összes képét.
     - **Válogatási Mód**:
       - *Manuális válogatás*: nincs AI, a képek egyszerűen visszakerülnek a kézi szortírozáshoz (Kanban vagy Szortírozó oldal).
       - *Csak AI Selejtezés*: az AI kizárólag a rossz (életlen, elsötétült, véletlen zsebfotó) képeket jelöli törlésre, a többi kategorizálatlan marad.
       - *Teljes AI (Selejt + Csoportosítás)*: az AI minden képhez javasol egy kategóriát, vagy törlésre jelöli.
     - AI mód választásakor megjelenik egy **AI Modell** választó (Flash-Lite – alapértelmezett és legolcsóbb, Flash, Pro Preview), és egy **"Egyéni törlési szempontok"** szövegmező, ahova saját szabályokat írhatsz (pl. "töröld, ha ujj lóg a lencsébe, de ne töröld, ha kutya van rajta"). Ez a mező egy külső, szerkeszthető fájlba (`egyeni_torlesi_szempontok.txt`) mentődik, és onnan is töltődik be induláskor — kívülről is szerkesztheted, és ha itt kiürítöd, a fájl tartalma is törlődik.
   - Válaszd ki a feldolgozandó mappát a jobb oldali böngészőben, majd kattints a **Folyamat Indítása** gombra.
   - A rendszer megjelöli a képeket, majd (AI mód esetén) a háttérben elkezdi elemezni őket a Gemini API-n keresztül, egy beépített tempókorláttal (hogy az ingyenes API-kvótán belül maradjon). Egy folyamatjelző sáv mutatja az állást, és menet közben bármikor leállítható.
   - **Jóváhagyás**: az AI javaslatai nem kerülnek automatikusan mentésre. A **"AI Jóváhagyás"** gombbal (vagy a `/review` oldalon) egy ugyanolyan Kanban-táblát látsz, csak itt az AI saját javaslata szerinti oszlopban jelenik meg minden kép. Itt:
     - áthúzhatod bármelyik képet egy másik kategóriába, ha nem értesz egyet a javaslattal (egyesével vagy több kijelölt képpel együtt),
     - egyesével elfogadhatod egy kép jobb alsó pipa gombjával,
     - vagy egyszerre az **Összes Elfogadása** / **Összes Elvetése** gombbal döntheted el az összes függőben lévő javaslat sorsát (az elvetett képek besorolatlanként visszakerülnek a kézi szortírozóba).
     - A képre kattintva megnyíló nagyítóban ugyanazok a billentyűk működnek, mint a Kanbanban: **PageUp/PageDown** lapozás a kategórián belül, **L/R** forgatás, **Delete** a Törlendő oszlopba helyezés (itt azonnali mentéssel, mert a Jóváhagyó nézetnek nincs külön Mentés lépése).
   - **Duplikátum-szűrés**: a rendszer az AI-elemzés előtt felismeri a nagyon hasonló, egymás utáni képeket (pl. sorozatfelvételek, kis kameramozdulással készült párok), és csoportonként egyszerre vizsgálja őket, hogy csak a legjobb példányt tartsa meg. Ha minden képen csukva van a szem, a jobb arckifejezésűt/mosolygósat részesíti előnyben. Nincs külön teendőd, a Folyamat Indítása automatikusan használja.
   - **Várakozás közben**: a folyamatjelző sáv mellett pörgő pontsor és játékos státuszfeliratok jelzik, hogy az AI dolgozik.
   - **Hibák**: ha az AI korlát vagy modellhiba miatt egy másik modellre vált, vagy egy kép elemzése nem sikerül, a Jóváhagyó oldalon figyelmeztető sáv jelenik meg, a sikertelen képek pedig a Szortírozóban maradnak.

10. **Lomtár kezelése**:
   - A szortírozó kártyán látható a törlésre váró képek száma. A **Lomtár Átnézése** gombbal megnyithatod a listát, ahol a nem kívánt fotókat véglegesen törölheted a Backblaze B2 felhőtárhelyről (a bélyegképek is törlődnek).
   - **Visszaállítás**: a Lomtárból egyesével vagy az **Összes visszaállítása** gombbal visszahozhatod a képeket; ezek azonnal megjelennek a Szortírozóban.

11. **Vetítés szűrése időszak szerint (Slideshow Setup)**:
   - A Slideshow Setup oldalon a **Shuffle All Photos** gomb alatt találod a **Hó / Hét / Nap** gyorsgombokat (zöld lejátszás-ikon és a feloldott dátum látható mellettük). Egy kattintással azonnal elindul a vetítés csak az utolsó 30 nap / 7 nap / 1 nap fotóival, véletlen sorrendben (gördülő időablak, nem naptári hónap; az EXIF-dátum alapján).
   - A szűrő az URL-ben is megmarad (megosztható, újratöltés után is él), és a Chromecastra küldéskor is érvényes.
   - A szűrő a kép **készítésének ideje** alapján dönt (a fájlnévből és a mappából kiolvasva), nem a feltöltés ideje szerint. Ha egy képnél a készítés ideje nem állapítható meg (jellemzően régi Takeout-képek, amelyek mappájában csak év és hónap van), az a kép a dátumszűrt vetítésből kimarad. A szűrő nélküli vetítésben (pl. Shuffle All Photos) minden kép játszik.
   - A beállítások alsó sora: **Idő (s)** (képváltási idő), **Kategória** és **Nevek** kapcsoló (alapból bekapcsolva); telefonon 2×2 rácsban jelennek meg.

12. **Gyors kategorizálás vetítés közben**:
   - A vetítő nézetben a Zászló (Flag) gomb mellett található **Kategorizálás** ikonra kattintva felugrik a kategóriák listája (a „Törlés (AI)" rendszerkategória nélkül). Válassz egyet, és a most látható kép besorolása azonnal mentődik — ugyanúgy, mint a Kanbanban.

13. **Telefonról érkező képek automatikus feltöltése (FolderSync)**:
   - Telepítsd a telefonra a **FolderSync** alkalmazást, és állítsd be, hogy a kamera-mappát a `beerkezo` B2-vödörbe szinkronizálja (részletes beállítás: `android_auto_feltoltes/folder_sync_setup_utmutato.md`).
   - A Lumina szervere 5 percenként magától feldolgozza a beérkezett képeket: kiszűri a duplikátumokat és a korábban szándékosan törölt képeket (SHA1 alapján), dátum szerint Év/Hónap mappába rendezi, bélyegképet készít, és a képek megjelennek a Luminában — kézi Sync nélkül.
   - Ha nem akarsz 5 percet várni, a feldolgozás azonnal elindítható a `POST /api/incoming/process-now` végponttal.
   - Fontos: a FolderSync-ben a fájlméret-ellenőrzést ki kell kapcsolni — a feldolgozott fájl helyén egy 0 bájtos helyjelölő marad, hogy a kép ne töltődjön fel újra.

14. **Szinkronizálás és biztonság (háttérben)**:
   - A **teljes B2-szinkron** nem töröl el képet az adatbázisból pusztán azért, mert a felhő listázása átmenetileg kihagyta; előbb külön ellenőrzi, hogy a fájl valóban hiányzik-e.
   - Szinkron után a rendszer automatikusan újragenerálja a hiányzó bélyegképeket (ha egy kép feketén vagy üresen látszik a felületen, futtass egy szinkront).
   - **Szortírozó Pánik gomb**: a várólista azonnali ürítésére szolgál, ha valami elakadt.

15. **Haladó beállítások (környezeti változók)**:
   - `GEMINI_RPM_LIMIT`: percenkénti AI-kérések száma (alap: 12 az ingyenes kvótához; fizetős kulccsal magasabb, pl. 900).
   - `GEMINI_MAX_CONCURRENCY`: egyszerre feldolgozott képek száma (alap: 1).
   - `DUPLICATE_HASH_THRESHOLD`, `DUPLICATE_HASH_LOOSE_THRESHOLD`, `DUPLICATE_TIME_GAP_SECONDS`: a duplikátum-felismerés érzékenysége (alap: 10 / 28 / 15 mp).
   - Az API-kulcsokat a `.env` fájlban tárold (ez git-ignorált; ne kerüljön verziókezelésbe).
