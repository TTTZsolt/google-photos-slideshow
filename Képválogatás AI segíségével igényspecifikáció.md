# Képválogatás AI segítségével - Igényspecifikáció

## 1. Cél
A Képnézegető alkalmazás kibővítése AI-alapú képválogatási, selejtezési és csoportosítási funkciókkal, amelyek megkönnyítik és felgyorsítják a nagyszámú fotó feldolgozását.

## 2. A válogatási folyamat (Mover-ből indítva)
Amikor a felhasználó a Mover (Tömeges mozgatás/Kijelölés) felületen bejelöl képeket válogatásra, három lehetőség közül választhat:

*   **a) Manuális válogatás:** A felhasználó saját maga dönti el minden képnél, hogy törli-e (Lomtárba helyezi), vagy valamilyen csoporthoz/albumhoz rendeli. (A jelenlegi, hagyományos működés kényelmesebb formája).
*   **b) AI-alapú selejtezés ("felesleges" képek):** Az AI (a képek thumbnail-jeit elemezve) megjelöli a rosszul sikerült, homályos, duplikált vagy feleslegesnek ítélt képeket törlésre. 
*   **c) AI-alapú teljes válogatás (Selejtezés + Csoportosítás):** Az AI nem csak a felesleges képeket jelöli ki törlésre, hanem a megtartandó képeket tematikus csoportokhoz (pl. "Tájképek", "Család", "Dokumentumok") is hozzárendeli.

*Technikai megjegyzés: Az AI elemzéshez a gyorsaság és költséghatékonyság érdekében a képek kisképei (thumbnail-jei) lesznek elküldve.*

## 3. Az AI javaslatok ellenőrzése és jóváhagyása (Review folyamat)
Mivel az AI tévedhet, minden automatikus döntést a felhasználónak kell jóváhagynia.

### 3.1. Törlésre (Lomtárba) javasolt képek ellenőrzése
Az AI által "feleslegesnek" ítélt képek automatikusan a **Lomtárba** (Recycle Bin) kerülnek, mint "törlésre javasolt" elemek. 
*   **Ellenőrzés:** A felhasználó a Lomtár felületén nézheti át ezeket.
*   **Új funkció a Lomtárban:** A Lomtár felülete kiegészül egy **"Összes kép visszaállítása"** gombbal, amellyel egy kattintással vissza lehet vonni a téves vagy meggondolt tömeges törléseket. Szükség esetén az egyes képek egyenként is visszaállíthatók.

### 3.2. Csoporthoz rendelésre javasolt képek ellenőrzése
*[Tervezés alatt - A felhasználóval való egyeztetés alapján töltjük ki. Lásd az alternatívákat a beszélgetésben.]*

## 4. Technikai követelmények és mérföldkövek
1.  **Lomtár fejlesztése:** "Összes kép visszaállítása" funkció implementálása.
2.  **Mover felület bővítése:** A három válogatási opció (Manuális, AI selejtezés, AI teljes válogatás) kiválasztási lehetőségének kialakítása.
3.  **AI integráció:** A thumbnail-ek elküldése és az eredmények feldolgozása.
4.  **Jóváhagyó felület (Review):** A besorolások ellenőrzésére szolgáló UI kialakítása.
