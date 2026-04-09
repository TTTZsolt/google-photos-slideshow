# Javasolt Git Munkafolyamat a Képnézegető Projekthez

Ez a dokumentum összefoglalja a biztonságos hibajavítás és fejlesztés lépéseit.

## 1. Új javítás vagy funkció indítása (Branching)

Soha ne fejlessz közvetlenül a `main` ágon. Hozz létre egy külön ágat a javításnak:

```bash
# 1. Biztosítsd, hogy a main ágon állsz
git checkout main

# 2. Hozz létre egy új ágat a javításnak
git checkout -b v13-javitasok
```

## 2. Fejlesztés és mentés (Commit)

Végezd el a módosításokat a kódban, majd mentsd el őket:

```bash
# 3. Add hozzá a változtatott fájlokat
git add .

# 4. Készíts egy commit-ot leírással
git commit -m "V13.7: Dashboard UI javítása és gombok igazítása"
```

## 3. Összefűzés a fő ággal (Merge)

Ha elkészültél és letesztelted a javítást, olvaszd be a `main` ágba:

```bash
# 5. Válts vissza a main ágra
git checkout main

# 6. Olvaszd be a javításokat tartalmazó ágat
git merge v13-javitasok

# 7. (Opcionális) Töröld a segéd-ágat, ha már nincs rá szükség
git branch -d v13-javitasok
```

## 4. Verziózás és feltöltés (Tag & Push)

Végül rögzítsd az új verziót és töltsd fel a GitHub-ra:

```bash
# 8. Hozz létre egy új verzió címkét
git tag -a v13.7 -m "Verzió 13.7: Stabil UI javítások"

# 9. Töltsd fel a kódod és a címkéket a GitHub-ra
git push origin main --tags
```

---

### Miért jó ez a módszer?
- **Biztonság**: A `main` ágad mindig stabil marad.
- **Visszakövethetőség**: Minden javításnak nyoma van a történetben.
- **Kísérletezés**: Akár több megoldást is kipróbálhatsz különböző ágakon.
