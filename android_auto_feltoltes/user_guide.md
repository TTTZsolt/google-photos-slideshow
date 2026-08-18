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

Másold át ezeket a fájlokat a telefonra, a Termux home könyvtárába egy `lumina_auto_feltoltes` almappába:
- `upload_lib.sh` (közös feltöltési logika - ezt a másik két script használja)
- `lumina_watcher.sh` (automatikus figyelő)
- `manual_upload.sh` (kézi, kiválasztásos feltöltés - l. 6. pont)
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

## 6. Kézi, kiválasztásos feltöltés (ha az automatikus ki volt kapcsolva)

Ha egy kép akkor készült, amikor az automatikus feltöltés ki volt kapcsolva, utólag is felküldheted:

1. Egyszeri telepítés: a **Termux:API** appot is telepítsd F-Droid-ról (**ugyanarról a forrásról, mint a fő Termux appot** — ha eltér, a párbeszédablak nem fog működni, ugyanaz a probléma, mint a Termux:Widget-nél), majd:
   ```bash
   pkg install termux-api jq
   ```
2. Futtatás:
   ```bash
   bash ~/lumina_auto_feltoltes/manual_upload.sh
   ```
   Ez megmutatja a kamera-mappa legutóbbi (max. 50) képét egy kipipálható listában — jelöld ki, amit fel szeretnél tölteni, és a script a többit elintézi (ugyanazzal a logikával, mint az automatikus figyelő: Év/Hónap mappa, bélyegkép, Lumina-értesítés).
3. Ehhez is készíthetsz Widget-ikont (l. `shortcuts/Lumina kézi feltöltés.sh`).

## Ismert korlátok

- A figyelés **valós idejű** (`inotifywait`) — ha a figyelő folyamat véletlenül leáll (pl. Android lekilövi a háttérben), és közben készül egy fotó, azt **nem** fogja utólag automatikusan észrevenni, amikor újraindul. Erre való a fenti **6. pont (kézi feltöltés)** — azzal utólag pótolható.
- HEIC-fájlok JPG-vé konvertálása az `imagemagick`-kel történik; ha ez lassú a telefonon, jelezd, más módszert is választhatunk.
- A `clean_string()` névtisztítás bash-ben van megvalósítva (nem Python), a legtöbb esetben ugyanazt az eredményt adja, mint a PC-s eszközök, de nagyon egzotikus fájlnevek esetén apró eltérés előfordulhat.
