# Google Photos Slideshow - Rendszer Dokumentáció (V8.3)

Ez a dokumentáció részletesen összefoglalja a Google Photos Slideshow rendszer működését, felépítését és használatát, amely a feltöltött Backblaze B2 képeidet vetíti ki egyedileg konfigurálható kijelzőkre.

## 1. Fő Funkciók

A rendszer több egyedi megoldást tartalmaz a folyamatos képvetítés és karbantartás érdekében:

*   **Villódzásmentes Slideshow (Flicker-Free Transitions)**: A megjelenítő böngészős felület (Receiver) egy intelligens, kettős pufferelési (*dual-buffer*) stratégiát használ. Miközben az egyik kép látható, a háttérben már töltődik a következő, így a képek közötti váltás CSS animációval (`opacity cross-fade`) teljesen zökkenőmentes, és nem jelenik meg villogás vagy töltőképernyő a váltások között.
*   **Optimalizált Backblaze B2 (Felhőtárhely) Kapcsolat**: A program nem tölti le sem előre, sem véglegesen a szerverre maga az egész képtárat! Ehelyett a dedikált szinkronizáló háttérfolyamat (`worker.py`) csak feltérképezi és indexeli a B2 felhőtárhely állományait egy helyi SQLite adatbázisba (`photos_app.db`). A megjelenítéskor az intelligens rendszer a fotókat közvetlenül a felhőből (egy Cloudflare proxyn keresztül) kéri le, míg a generált hozzáférési tokeneket cache-eli. Ez kiküszöböli a nagyszámú mappalekérdezéseket, így elkerülhetők a B2 API letöltési korlátai ("transaction cap exceeded").
*   **Központosított Vezérlés és Play/Pause**: A rendszer lelke egy mesterkapcsoló (`master_switch`), amelyet a Vezérlőpulton (Dashboard) találhatsz. Ezzel minden csatlakoztatott és vizualizáló kijelzőt egyszerre indíthatsz vagy állíthatsz le távolról.
*   **Beépített Chromecast (TV) Támogatás**: A szerver backend képes a hálózatodon található Chromecast-képes eszközöket (pl. Google TV) detektálni a beépülő `catt` (Cast All The Things) modul segítségével. Ezekre egyetlen kattintással kiküldhető a Slideshow weblapja, így a TV automatikusan a vetítés részévé válik.
*   **Képek Retusálása Játék Közben (Digitális Labor & Photopea)**: Ha egy vizuálisan hibás (pl. fejjel lefelé álló, vagy piros szemes) fotó tűnik fel a vetítésben, a kijelzőn (Receiver) lévő gombbal a kép **Megjelölhető (Flag)** javításra. Ezek a képek bekerülnek a Vezérlőpult "Retouch Queue / Digitális Labor" listájába, ahonnan közvetlenül, egy beépített webes képszerkesztőben (**Photopea**) megnyithatók és javíthatók. Mentéskor a rendszer a javított képet automatikusan a régi helyére tölti (a fájlnév végére illesztve a `-szerkesztett` szót), míg az eredeti, hibás példányt biztonsági okokból áthelyezi egy Archív B2 tárhelyre (Bucket).

---

## 2. Architektúra: Mi, hol fut?

A rendszer három fő logikai komponensből áll:

1.  **A Backend Szerver (A "Motor")**: 
    *   **Hol fut?** Jellemzően a helyi hálózati **Tableteden** (pl. `192.168.1.157-es IP címen`) Debian/Termux vagy Linux környezetben. A Windows gépedről a `start_tablet.bat` fájllal indíthatod (ami SSH-n keresztül küldi be a parancsot a tabletnek), de fizikailag a Python folyamat ott fut.
    *   **Mi ez?** Egy `FastAPI` és `SQLAlchemy` alapú Python alkalmazás. Ez tartja a kapcsolatot a Backblaze B2 API-val, menti a képek metaadatait az SQLite adatbázisba, nyomon követi melyik megjelenítő milyen mappát vetít, és biztosítja a véletlenszerű képválasztást (`slideshow.py`) úgy, hogy egy előkészített virtuális "kártyapakliból" húz képeket ismétlődés nélkül.
2.  **A Frontend Vezérlőpult / Dashboard (A "Távirányító")**:
    *   **Hol fut?** Bármelyik, a helyi hálózatra kötött okoseszköz böngészőjében (A Windows PC-d, Mac-ed, vagy akár a mobiltelefonod).
    *   **Mi ez?** A `backend/templates/index.html` alapú webes UI. Ezen a felületen keresztül tudod kezelni a B2 API kulcsokat, kijelölni a vetítendő mappát, és használni a beépített képszerkesztőt a hibás fotók esetében.
3.  **A Megjelenítő / Receiver (A "Kijelző")**:
    *   **Hol fut?** Azokon az eszközökön, amiken magát a képet szeretnéd látni. Ez lehet a nappaliban lévő Okos TV (Chromecast), egy fali Tablet böngészője, vagy egy számítógép dedikált másodlagos monitora.
    *   **Mi ez?** A `backend/templates/receiver.html` alapú weboldal. JavaScript segítségével periodikusan (alapértelmezett: 240 mp) kommunikál a Backend Szerverrel új képért, életjel (heartbeat) jeleket küld a Dashboardnak magáról, és rendereli a képcserélő CSS animációt.

---

## 3. Fontos Linkek (Hálózati Végpontok)

Feltételezve, hogy a Backend Szerver a Tableten a **`192.168.1.157`** IP címen, a **`8080`**-as porton fut:

*   **Vezérlőpult (Dashboard)**
    `http://192.168.1.157:8080/`
    Itt végezhető el a teljes adminisztráció (Tárhely beállítása, Vezérlés, Labor).
*   **Képmegjelenítő (Slideshow Receiver)**
    `http://192.168.1.157:8080/receiver`
    Ezt a linket kell megnyitni a céleszközökön (TV, Tablet). Opcionális URL paramétereket is fogad (pl. a képváltási idő felülbírálása: `.../receiver?interval=120`, de alapértelmezettként a V8.0-tól ez már 240 másodperc).
*   **Belső Rendszer Linkek (A program logikája által hívottak, manuálisan nem kell használni őket)**:
    *   `/api/media/random`: Egy véletlenszerű fotó adatait és titkosított URL-jét adja ki a Slideshow-nak.
    *   `/api/folders`: A B2 bucketből kilistázott alkönyvtárakat nyújtja.
    *   `/api/system/status`: Riport a nyitott Receiver-ek állapotáról a Dashboard felé.
    *   `/api/photopea/save`: Ide érkezik meg a webről a Photopea-ban módosított fotó, hogy a backend visszaírja az eredeti helyére.
    *   `/slideshow/cast` és `/slideshow/stop-cast`: A Chromecast parancsokat kezeli távolról.

---

## 4. Használati Útmutató (Lépésről Lépésre)

### 1. A Rendszer Indítása
A Windows PC-d projekt mappájában (`C:\Users\zsolt.tuske\...`) futtasd a **`start_tablet.bat`** parancsfájlt.
Ez SSH protokollon keresztül csatlakozik a Tabletre, elindítja a szervert a háttérben, majd a Windows gépen azonnal meg is nyitja neked a Chrome böngészőből a Vezérlőpultot. *(Megjegyzés: Ha frissítést kaptál a GitHub-ról, a Tablet frissítése manuális SSH belépéssel, vagy a batch fájlokba drótozva történik).*

### 2. Kezdeti Szinkronizáció
Miután megnyílt a Vezérlőpult a PC-den (`192.168.1.157:8080`):
- A "B2 Account" kártyán ellenőrizd a Backend kapcsolatot (Key ID, App Key, vödrök meglétét stb).
- Ha új fotókat töltöttél fel a Backblaze szervereire, kattints az account melletti kék **[Resync]** gombra. Ekkor a háttérben futó worker megkezdi a felhő feltérképezését és eltárolja a fájlok útvonalait helyben, hogy gyorsabb legyen a lejátszás. Ezt meg kell várni (a folyamat kiírja, hány sort indexelt már).

### 3. A Vetítés Indítása és a TV (Chromecast) Használata
- A Vezérlőpulton a Mappák közül (bal oldal / Főoldal) válaszd ki, hogy melyik eseményt/albumot szeretnéd lejátszani (vagy hagyd Alapértelmezetten a teljes gyökérkönyvtárat).
- Kattints a hatalmas **Play gombra (Start Slideshow)**.
- Ha közvetlenül a Nappali okostévéjén akarod nyitni a képeket, tekerj a Vezérlőpult aljára a felismert Chromecast eszközökhöz. Válaszd ki pld. a *"Nappali TV"*-t, majd nyomd meg a **TV (Cast) ikont**. A TV azonnal megnyitja a `/receiver` oldalt magán, és pár másodpercen belül elkezdődik a képvetítés.

### 4. Menet Közbeni Módosítás (Hibás Kép "Megjelölése")
Előfordulhat, hogy a fotó, amit épp a Receiver vetít, rosszul van rotálva vagy egyéb problémás dolog van rajta.
Amikor egy ilyen kép van a kijelzőn:
- Lépj oda a Tablethez (vagy használd az egeret asztali monitoron) és kattints az éppen látható fotón lévő vékony akcióikonok egyikére a sarokban: a **Zászló / Megjelölés ikonra**.
- A kép ekkor egy piros kerettel jelzi, hogy regisztrálta a kérést. Bekerült az adatbázis hibás (`FlaggedImage`) fotókat tartalmazó táblájába, ezután a vetítés normálisan folytatódik (240 másodperc múlva továbblép).

### 5. A Hibás Képek Retusálása (Digitális Labor)
Bármikor a jövőben, amikor időd engedi, ülj le a Vezérlőpult (PC) elé.
- A Vezérlőpult legalján találsz egy szekciót: **"Digitális Labor (Retouch Queue)"**.
- Lenyitva azonnal kilistázza a fotókat, amiket a Receiver eszközökön valaki megzászlóztatott.
- A kívánt hibás fotó mellett kattints a **Photopea (kék)** ikonra. Ekkor felpattan a böngésződben az integrált Photopea (webes Photoshop), betöltve azonnal az adott képet teljes felbontásban.
- Fordítsd el, állítsd a fehéregyensúlyt vagy vágd meg a képet (Image -> Transform stb.).
- Mikor kész vagy, válaszd a **File -> Save** opciót (bal felső sarokban).
- A Photopea közli a sikeres mentést. A háttérben a program ekkor fogja a most manipulált adataidat feltölti a B2 rendszerre `-szerkesztett` névvel a végén, miközben biztonsági okokból a régi eredeti fotót átmenti az Edit Archive (kepek01) Backblaze vödörbe!
- Zárhatod a Photopea-t, a kép lekerül a Labor listájáról. Kész vagy.

### 6. Képek hozzáadása, majd kategorizálása
Amikor új képeket szeretnél a rendszerhez adni (pld. a Google Photos-ból), először a `forras` vödörbe kell őket feltöltened. Ezt követően a rendszer észleli őket, amint rányomsz a **[Resync]** gombra a B2 Account kártyán.
A képek kategorizálásához végezd el az alábbi lépéseket:
1. Nyisd meg a Vezérlőpult (Dashboard) oldalát, és kattints a "Fotó Szortírozó" kártyán lévő **Indítás Mobilon** gombra. Ezt érdemes a telefonodról vagy egy kényelmes érintőképernyős eszközről megtenni.
2. A megnyíló felületen (Tinder-stílusban) húzz egyet az ujjaddal a képernyőn a megjelenő képen:
   - **Jobbra húzás**: Család kategória
   - **Balra húzás**: Utazás kategória
   - **Lefelé húzás**: Állatok / Növények kategória
   - **Felfelé húzás**: Törlés (a kép a B2-tárolón is átkerül a biztonsági `torles-elott` vödörbe)
3. A besorolt képek az adatbázisban végleges rögzítésre kerülnek és valós időben átkerülnek a fizikai B2 tárolón is az aktív vetítésért felelős `kepek02` vödörbe.

### 7. Képek újra kategorizálása (Visszamozgató)
Ha egy korábbi mappát vagy kategória nélküli (régi) képeket szeretnél újra átszortírozni (akár azért, mert hibáztál, akár a régi gyűjteménnyel kezdesz neki a rendszer használatának):
1. Irány a Vezérlőpult jobb oldali panelje, a **Visszamozgató** szekció.
2. Dönthetsz úgy, hogy egy adott mappára szűrsz (pl. `2024/Januar/`), vagy hagyhatod üresen a teljes könyvtárra.
3. Kategória szerint kiválaszthatod, hogy csak a "kategorizálatlan" képeket (alapértelmezett) mozgassa vissza, vagy adott kategóriát. (Kategorizálatlannak számít minden "régi" fotó, amit még a V9.0 előtt egyből a `kepek02`-be töltöttél).
4. Kattints az **Indítás** gombra.
5. A folyamat a háttérben zajlik, haladását láthatod a megjelenő folyamatjelző csíkon (Progress bar).
6. A művelet fizikailag átmozgatja a `kepek02`-ből a fájlokat vissza a `forras` vödörbe, és lenullázza az eddigi kategóriájukat az adatbázisban, hogy ismét felbukkanjanak a "Fotó Szortírozó" felületén, ahonnan újra besorolhatod őket.
