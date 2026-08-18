# Android automatikus fényképfeltöltés — Beüzemelési útmutató

## Mit csinál

Amikor bekapcsolod, a telefonod kamera-mappáját (`DCIM/Camera`) figyeli, és minden új fotót **automatikusan feltölt közvetlenül a Lumina `Kepek02` vödrébe** (Év/Hónap mappastruktúrával, EXIF-dátum alapján, `mappazasi_algoritmus_specifikacio.md` szerint). A feltöltött kép **kategória nélkül, de azonnal vetíthető** — a kategorizálás (ha szeretnéd) a Mover + Szortírozó felületen, opcionálisan, bármikor később elvégezhető.

**Be- és kikapcsolható** egyetlen paranccsal, bármikor — nem kell hozzá a telefonhoz mást tenned, csak elindítani/leállítani a feltöltést.

---

## 1. Egyszeri telepítés (Termux)

1. Telepítsd a **Termux**-ot (F-Droid-ról ajánlott, nem a Play Store-ból, mert az elavult).
2. Telepítsd a **Termux:Boot** appot is (ugyanattól a fejlesztőtől, F-Droid), hogy telefon-újraindítás után automatikusan induljon a figyelő.
3. Nyisd meg a Termux-ot, és futtasd:
   ```bash
   pkg update && pkg upgrade
   pkg install inotify-tools rclone exiftool imagemagick coreutils
   termux-setup-storage
   ```
   A `termux-setup-storage` egy engedélykérő ablakot dob fel — engedélyezd, hogy a Termux hozzáférjen a telefon tárhelyéhez (ez teszi elérhetővé a `~/storage/dcim/Camera` mappát).
4. Állítsd be az `rclone`-t a Backblaze B2 eléréshez:
   ```bash
   rclone config
   ```
   Hozz létre egy `b2_storage` nevű remote-ot (ugyanazokkal a B2 Key ID / Application Key adatokkal, amiket a Lumina Dashboardon is használsz — a "B2 Kapcsolat" kártyán találod őket).

## 2. A scriptek elhelyezése

Másold át ezt a négy fájlt a telefonra, a Termux home könyvtárába egy `lumina_auto_feltoltes` almappába:
- `lumina_watcher.sh`
- `start_auto_feltoltes.sh`
- `stop_auto_feltoltes.sh`
- `status_auto_feltoltes.sh`

(Legegyszerűbben: ha a Google Drive alkalmazás telepítve van a telefonon, ezek a fájlok elérhetők a Drive-on keresztül is — másold be őket a Termux-ba, pl. a `termux-setup-storage` után elérhető megosztott tárhelyről `cp` paranccsal.)

Majd tedd futtathatóvá őket:
```bash
cd ~/lumina_auto_feltoltes
chmod +x *.sh
```

## 3. Termux:Boot beállítása (automatikus indulás újraindítás után)

```bash
mkdir -p ~/.termux/boot
cp termux_boot_start_lumina_watcher.sh ~/.termux/boot/
chmod +x ~/.termux/boot/termux_boot_start_lumina_watcher.sh
```

Ezután nyisd meg egyszer a **Termux:Boot** appot is a telefonon (üres ablak, de az első megnyitás szükséges ahhoz, hogy az Android engedélyezze neki az automatikus indulást).

## 4. A figyelő elindítása (most, első alkalommal)

```bash
cd ~/lumina_auto_feltoltes
nohup bash lumina_watcher.sh >> ~/lumina_auto_upload.log 2>&1 &
```

Ez a figyelő folyamat ezután **folyamatosan fut a háttérben** (és túléli a telefon-újraindítást is, a Termux:Boot miatt) — de **önmagában még nem tölt fel semmit**, amíg be nem kapcsolod.

## 5. Napi használat

```bash
bash ~/lumina_auto_feltoltes/start_auto_feltoltes.sh    # bekapcsolás
bash ~/lumina_auto_feltoltes/stop_auto_feltoltes.sh     # kikapcsolás
bash ~/lumina_auto_feltoltes/status_auto_feltoltes.sh   # állapot + napló ellenőrzése
```

**Tipp**: ezekhez a Termux widgeten (Termux:Widget app) keresztül egy-egy ikont is létrehozhatsz a telefon kezdőképernyőjén, hogy ne kelljen a parancsokat begépelned.

## Ismert korlátok

- A figyelés **valós idejű** (`inotifywait`) — ha a figyelő folyamat véletlenül leáll (pl. Android lekilövi a háttérben), és közben készül egy fotó, azt **nem** fogja utólag észrevenni, amikor újraindul. Ha ez problémát okoz, jelezd — megoldható egy időszakos "utólagos átvizsgálás" hozzáadásával is.
- HEIC-fájlok JPG-vé konvertálása az `imagemagick`-kel történik; ha ez lassú a telefonon, jelezd, más módszert is választhatunk.
- A `clean_string()` névtisztítás bash-ben van megvalósítva (nem Python), a legtöbb esetben ugyanazt az eredményt adja, mint a PC-s eszközök, de nagyon egzotikus fájlnevek esetén apró eltérés előfordulhat.
