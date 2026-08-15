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

6. **Fotók válogatása (Szortírozó)**:
   - Nyisd meg a Dashboardról (lehetőleg telefonon/tableten) a **Szortírozót**.
   - Egyszerre egy kép jelenik meg nagyban; a jobb alsó sarokban egy kis előnézetben látszik az előzőleg besorolt kép.
   - **Besorolás**: koppints a kép alatt megjelenő kategória-gombok egyikére (ezek a nálad definiált kategóriák, saját ikonnal és színnel) — a kép azonnal átkerül a megfelelő csoportba, és betöltődik a következő.
   - **Törlés**: koppints a bal alsó **Törlés** gombra — a kép a Lomtárba kerül.
   - **Visszavonás (Undo)**: koppints a jobb alsó sarokban látható kis előnézeti képre (ez mindig az utoljára besorolt kép) — ezzel visszavonod az utolsó döntést, és a kép újra a várólista elejére kerül.
   - **Nagyítás**: két ujjal csippentve (pinch-to-zoom) nagyíthatod és mozgathatod az aktuális képet alaposabb megtekintéshez. Noteszgépen, érintőképernyő nélkül is elérhető: **Ctrl + görgetés** vagy trackpad-csippentés a nagyításhoz, bal egérgombbal húzva pedig mozgathatod a nagyított képet.
   - **Teljes képernyő**: a jobb felső maximalizáló ikonnal válthatsz zavartalan, teljes képernyős módra.
   - **Szortírozó ürítése**: a jobb felső körkörös nyíl ikonnal kiürítheted a várólistát (a képek megmaradnak, csak a "szortírozandó" jelölés törlődik).

7. **Képek manuális "huzogatással" történő csoportosítása (Mappa Kanban)**:
   - **Megnyitás**: A Dashboardon nyisd meg a **Visszamozgató (Mover)** modult, a jobb oldali Mappaböngészőben navigálj a kívánt mappához, majd kattints a mappa neve melletti kis mappa-ikonra ("Képek megnyitása a Kanban nézetben"). Ez megnyitja az adott mappa képeit a Kanban nézetben.
   - **Oszlopok**: A tábla oszlopai balról jobbra: **Törlendő**, **Besorolatlan**, majd egy-egy oszlop minden nálad definiált kategóriának (pl. Család, Utazás, stb.).
   - **Húzás**: Fogd meg egérrel (vagy érintéssel) egy kép kártyáját, és húzd át a kívánt oszlopba. A kép azonnal átkerül a felületen, de **még nincs elmentve** — a módosított képeken egy apró sárga pötty jelenik meg.
   - **Több kép egyszerre**: Kattintással jelölj ki képeket (Ctrl+kattintás: hozzáadás a kijelöléshez; Shift+kattintás: tartomány kijelölése ugyanazon oszlopon belül), majd húzd el bármelyik kijelölt kártyát — az összes kijelölt kép együtt mozog át az új oszlopba.
   - **Nagyítás**: Dupla kattintással megnyithatod a kép nagyméretű előnézetét.
   - **Mentés**: Ha végeztél a rendezéssel, kattints a **Változások Mentése** gombra. Csak ekkor íródnak a módosítások az adatbázisba, és csak ekkor mozognak a fájlok ténylegesen a Backblaze B2-ben (a háttérben).
   - **Korlát**: Egy mappában egyszerre legfeljebb 100 kép jelenik meg (teljesítmény miatt). Ha ennél több van, egy figyelmeztető sáv jelzi ezt, és mentés után automatikusan betöltődik a következő adag.

8. **AI-alapú előszűrés és -előkészítés**:
   - **Indítás**: Ugyanabban a **Visszamozgató (Mover)** modulban, a bal oldali panelen:
     - **Szűrés kategóriára**: eldöntheted, hogy csak a még kategorizálatlan képeket vonja be a folyamat, vagy az adott mappa/kategória összes képét.
     - **Válogatási Mód**:
       - *Manuális válogatás*: nincs AI, a képek egyszerűen visszakerülnek a kézi szortírozáshoz (Kanban vagy Szortírozó oldal).
       - *Csak AI Selejtezés*: az AI kizárólag a rossz (életlen, elsötétült, véletlen zsebfotó) képeket jelöli törlésre, a többi kategorizálatlan marad.
       - *Teljes AI (Selejt + Csoportosítás)*: az AI minden képhez javasol egy kategóriát, vagy törlésre jelöli.
     - AI mód választásakor megjelenik egy **AI Modell** választó, és egy **"Egyéni törlési szempontok"** szövegmező, ahova saját szabályokat írhatsz (pl. "töröld, ha ujj lóg a lencsébe, de ne töröld, ha kutya van rajta"). Ez a mező egy külső, szerkeszthető fájlba (`egyeni_torlesi_szempontok.txt`) mentődik, és onnan is töltődik be induláskor — kívülről is szerkesztheted, és ha itt kiürítöd, a fájl tartalma is törlődik.
   - Válaszd ki a feldolgozandó mappát a jobb oldali böngészőben, majd kattints a **Folyamat Indítása** gombra.
   - A rendszer megjelöli a képeket, majd (AI mód esetén) a háttérben elkezdi elemezni őket a Gemini API-n keresztül, egy beépített tempókorláttal (hogy az ingyenes API-kvótán belül maradjon). Egy folyamatjelző sáv mutatja az állást, és menet közben bármikor leállítható.
   - **Jóváhagyás**: az AI javaslatai nem kerülnek automatikusan mentésre. A **"AI Jóváhagyás"** gombbal (vagy a `/review` oldalon) egy ugyanolyan Kanban-táblát látsz, csak itt az AI saját javaslata szerinti oszlopban jelenik meg minden kép. Itt:
     - áthúzhatod bármelyik képet egy másik kategóriába, ha nem értesz egyet a javaslattal (egyesével vagy több kijelölt képpel együtt),
     - egyesével elfogadhatod egy kép jobb alsó pipa gombjával,
     - vagy egyszerre az **Összes Elfogadása** / **Összes Elvetése** gombbal döntheted el az összes függőben lévő javaslat sorsát (az elvetett képek besorolatlanként visszakerülnek a kézi szortírozóba).

9. **Lomtár kezelése**:
   - A szortírozó kártyán látható a törlésre váró képek száma. A **Lomtár Átnézése** gombbal megnyithatod a listát, ahol a nem kívánt fotókat véglegesen törölheted a Backblaze B2 felhőtárhelyről.
