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

6. **Fotók válogatása és szortírozása (Tinder-mód)**:
   - Nyisd meg a Dashboardról (lehetőleg telefonon) a **Fotó Szortírozót**.
   - Húzd el a megjelenő képet az alábbiak szerint:
     - **Jobbra húzás**: Család kategória
     - **Balra húzás**: Utazás kategória
     - **Lefelé húzás**: Egyéb egyedi kategória
     - **Felfelé húzás**: Törlés (a Lomtárba helyezi a képet)
   - Bármikor visszavonhatod az utolsó mozdulatot az **Undo (Visszavonás)** gombbal.

7. **Lomtár kezelése**:
   - A szortírozó kártyán látható a törlésre váró képek száma. A **Lomtár Átnézése** gombbal megnyithatod a listát, ahol a nem kívánt fotókat véglegesen törölheted a Backblaze B2 felhőtárhelyről.
