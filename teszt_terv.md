# AI Képválogatás - Teszt Terv (V16.1.0)

Ez a dokumentum a **V16.1.0** (Képválogatás AI segítségével) verzió asztali (desktop) környezetben történő manuális ellenőrzését támogatja. Kérlek, a tesztelés során jelöld be a sikeresen teljesült eseteket (`[x]`).

---

## 1. Előkészítés és Szerver Indítás

| Állapot |  ID  | Teszt Terület   | Teszt lépések                                         | Elvárt működés                                                                                | Megjegyzés |
| :-----: | :--: | :-------------- | :---------------------------------------------------- | :-------------------------------------------------------------------------------------------- | :--------- |
|   [x]   | T1.1 | Szerver indítás | Futtasd a `notebook_start_kepnezegeto.bat` fájlt.     | A Flask backend elindul hiba nélkül, és megnyílik a böngésző a `http://localhost:8000` címen. |            |
|   [x]   | T1.2 | Verziószám      | Ellenőrizd a fejlécben vagy láblécben a verziószámot. | A felületen a **V16.1.0-dev** (vagy hasonló V16.1.0-s) verziószám látható.                    |            |

---

## 2. Mover Felület (Válogatás Indítása)

| Állapot |  ID  | Teszt Terület      | Teszt lépések                                                                                              | Elvárt működés                                                                                                | Megjegyzés |
| :-----: | :--: | :----------------- | :--------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ | :--------- |
|   [x]   | T2.1 | Opciók megjelenése | Nyisd meg a **Mover** (Visszamozgató) modult a főoldalról.                                                 | A felületen egyértelműen megjelenik a 3 választási opció: *Manuális*, *AI selejtezés*, *AI teljes válogatás*. |            |
|  [x ]   | T2.2 | AI indítás         | Válassz ki egy mappát a listából, jelöld be az **AI teljes válogatás** opciót, majd kattints az indításra. | A rendszer elindítja a folyamatot, és átirányít a jóváhagyó (Review) vagy várakozó képernyőre.                |            |

---

## 3. AI Jóváhagyó Felület (Review Kanban Board)

| Állapot |  ID  | Teszt Terület         | Teszt lépések                                                                          | Elvárt működés                                                                                                                                        | Megjegyzés                                                                                                                                                                                                                                                  |
| :-----: | :--: | :-------------------- | :------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   [ ]   | T3.1 | Oszlopok generálása   | Nyisd meg az **AI Jóváhagyás** oldalt (`/review` vagy a Moverből való átirányítással). | Megjelennek az oszlopok: *Törlendő*, *Bizonytalan* és a többi dinamikusan beolvasott egyedi kategória (pl. Család, Utazás).                           | 2008/04/budakeszi-kert könyvtrárral tesztelek, amiben 14 kép van. Törlési szempontok:<br>* életlen, bemozdult kép<br>* több hasonló kép esetén azt kellene kitörölni, amelyiken csukott valakinek a szeme<br>* több hasonló kép esetén ne legyen ismétlődés |
|   [ ]   | T3.2 | Kártyák és Képek      | Ellenőrizd a megjelenő képkártyákat.                                                   | Minden kártyán látható a kép előnézete (thumbnail), a fájlnév és egy kis "pipa" (Jóváhagyás) gomb.                                                    |                                                                                                                                                                                                                                                             |
|   [ ]   | T3.3 | Drag and Drop         | Fogj meg egy képet, és húzd át egy másik kategória oszlopába.                          | A kép kártyája átkerül az új oszlopba, a háttérben elmentődik a kategória módosítás, és megjelenik a sikeres mentést jelző értesítés (Toast).         |                                                                                                                                                                                                                                                             |
|   [ ]   | T3.4 | Darabszám számlálók   | Figyeld az oszlopok tetején lévő darabszám számlálókat kártyák mozgatásakor.           | A darabszámok valós időben frissülnek a mozgatásnak megfelelően.                                                                                      |                                                                                                                                                                                                                                                             |
|   [ ]   | T3.5 | Egyenkénti Jóváhagyás | Kattints egy kártya jobb alsó sarkában lévő kis **Pipa (Jóváhagyás)** gombra.          | A kép eltűnik az ellenőrző felületről, véglegesen a javasolt kategóriába kerül, és a Toast értesítés kiírja: *"Javaslat elfogadva."*                  |                                                                                                                                                                                                                                                             |
|   [ ]   | T3.6 | Összes Elfogadása     | Kattints a jobb felső sarokban lévő **"Összes Elfogadása"** gombra.                    | Egy megerősítő kérdés után az összes képen lévő javaslat elfogadásra kerül, a felület kiürül, és megjelenik a *"Nincs ellenőrzésre váró kép"* üzenet. |                                                                                                                                                                                                                                                             |

---

## 4. Lomtár (Trash) Fejlesztések

| Állapot | ID | Teszt Terület | Teszt lépések | Elvárt működés | Megjegyzés |
| :---: | :---: | :--- | :--- | :--- | :--- |
| [ ] | T4.1 | Visszaállítás gomb | Nyisd meg a **Lomtár** felületet. | A jobb felső sarokban vagy a műveleti sávban látható az **"Összes kép visszaállítása"** (Restore All) gomb. | |
| [ ] | T4.2 | Tömeges visszaállítás | Dobj pár képet a Lomtárba, majd kattints az **"Összes kép visszaállítása"** gombra. | Minden kép kiürül a lomtárból, visszakerül az adatbázisban a kiinduló állapotába, és a B2 felhőben is visszahelyeződik a megfelelő mappába. | |
| [ ] | T4.3 | Lomtár ürítés | Helyezz képet a Lomtárba, majd kattints a **"Lomtár ürítése"** gombra. | A Lomtár kiürül, a képek véglegesen törlődnek az adatbázisból és a Backblaze B2 felhőtárhelyről is. | |
