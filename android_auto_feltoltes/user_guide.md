# Android automatikus fényképfeltöltés — Beüzemelési útmutató (Termux, LEGACY)

> ⚠️ **2026-08-19-től ez a módszer elavult.** A jelenlegi, ajánlott megoldás
> nem igényel Termux-ot/SSH-t/scripteket a telefonon — egy kész, Play
> Áruház-os app (FolderSync) elég, a feldolgozás a szerveren, automatikusan
> történik. L. `folder_sync_setup_utmutato.md` ebben a mappában. Ezt a
> Termux-alapú leírást csak referenciának/tartaléknak hagytuk meg.

## Mit csinál

Amikor bekapcsolod, a telefonod kamera-mappáját (`DCIM/Camera`) figyeli, és minden új fotót **automatikusan feltölt közvetlenül a Lumina `Kepek02` vödrébe** (Év/Hónap mappastruktúrával, EXIF-dátum alapján, `mappazasi_algoritmus_specifikacio.md` szerint). A feltöltött kép **kategória nélkül, de azonnal vetíthető** — a kategorizálás (ha szeretnéd) a Mover + Szortírozó felületen, opcionálisan, bármikor később elvégezhető.

**Be- és kikapcsolható** egyetlen paranccsal, bármikor — nem kell hozzá a telefonhoz mást tenned, csak elindítani/leállítani a feltöltést.

Minden feltöltés előtt a script ellenőrzi a kép SHA1-tartalmát a Lumina szerverén: ha a kép **már fent van** a `Kepek02`-ben, vagy korábban **tudatosan törölve lett**, a feltöltés kimarad — ugyanaz a védelem, mint amit a Takeout-feltöltő eszköz használ, hogy véletlenül se duplikálódjon vagy "támadjon fel" egy szándékosan törölt kép.

---

## 1. Egyszeri telepítés (Termux)

1. Telepítsd a **Termux**-ot (F-Droid-ról ajánlott, nem a Play Store-ból, mert az elavult).
2. Telepítsd a **Termux:Boot** appot is (ugyanattól a fejlesztőtől, **ugyanarról az F-Droid forrásról**, mint a Termux-ot), hogy telefon-újraindítás után automatikusan induljon a figyelő.
   > ⚠️ **Fontos**: minden Termux-kiegészítő appot (Boot, Widget, API — ha később kellene) **ugyanarról a forrásról** telepíts, mint a fő Termux appot. Ha eltér, az Android nem enged megosztott hozzáférést közöttük, és rejtélyes, hibaüzenet nélküli hibák jönnek elő (l. "Ismert korlátok" lent).
3. Nyisd meg a Termux-ot, és futtasd:
   ```bash
   pkg update && pkg upgrade
   pkg install inotify-tools rclone exiftool imagemagick coreutils jq
   termux-setup-storage
   ```
   A `termux-setup-storage` egy engedélykérő ablakot dob fel — engedélyezd, hogy a Termux hozzáférjen a telefon tárhelyéhez (ez teszi elérhetővé a `~/storage/dcim/Camera` és `~/storage/shared` mappákat).
4. Állítsd be az `rclone`-t a Backblaze B2 eléréshez:
   ```bash
   rclone config
   ```
   Hozz létre egy `b2_storage` nevű remote-ot (ugyanazokkal a B2 Key ID / Application Key adatokkal, amiket a Lumina Dashboardon is használsz — a "B2 Kapcsolat" kártyán találod őket).

## 2. A scriptek elhelyezése

Másold át ezeket a fájlokat a telefonra, a Termux home könyvtárába egy `lumina_auto_feltoltes` almappába:
- `upload_lib.sh` (közös feltöltési logika - ezt a másik scriptek használják)
- `lumina_watcher.sh` (automatikus figyelő)
- `manual_upload.sh` (utólagos "flush" a kézi feltöltéshez - l. 6. pont)
- `start_auto_feltoltes.sh`
- `stop_auto_feltoltes.sh`
- `status_auto_feltoltes.sh`
- `termux_boot_start_lumina_watcher.sh` (a Termux:Boot ezt fogja indítani - l. 3. pont)

**A legegyszerűbb módja ennek (és minden további frissítésnek) az SSH-hozzáférés beállítása** — l. a "Függelék: SSH hozzáférés" szakaszt lent. Enélkül is megoldható Google Drive-on keresztül: ha a Google Drive alkalmazás telepítve van a telefonon, töltsd le róla a fájlokat (Letöltések mappába kerülnek), majd a Termux-ban `~/storage/downloads/<fájlnév>` útvonalról másold be őket `cp` paranccsal.

Majd tedd futtathatóvá őket:
```bash
cd ~/lumina_auto_feltoltes
chmod +x *.sh
```

## 3. Termux:Boot beállítása (automatikus indulás újraindítás után)

```bash
mkdir -p ~/.termux/boot
cp ~/lumina_auto_feltoltes/termux_boot_start_lumina_watcher.sh ~/.termux/boot/
chmod +x ~/.termux/boot/termux_boot_start_lumina_watcher.sh
```

Ezután nyisd meg egyszer a **Termux:Boot** appot is a telefonon (üres ablak, de az első megnyitás szükséges ahhoz, hogy az Android engedélyezze neki az automatikus indulást).

## 4. A figyelő elindítása (most, első alkalommal)

```bash
cd ~/lumina_auto_feltoltes
nohup bash lumina_watcher.sh >> ~/lumina_auto_upload.log 2>&1 &
```

Ez a figyelő folyamat ezután **folyamatosan fut a háttérben** (és túléli a telefon-újraindítást is, a Termux:Boot miatt) — de **önmagában még nem tölt fel semmit** a kamera-mappából, amíg be nem kapcsolod (l. 5. pont). A `Pictures/LuminaFeltoltes` mappát (l. 6. pont) viszont ettől a pillanattól kezdve mindig figyeli, függetlenül a be/kikapcsolt állapottól.

## 5. Napi használat (automatikus kamera-feltöltés be/ki)

```bash
bash ~/lumina_auto_feltoltes/start_auto_feltoltes.sh    # bekapcsolás
bash ~/lumina_auto_feltoltes/stop_auto_feltoltes.sh     # kikapcsolás
bash ~/lumina_auto_feltoltes/status_auto_feltoltes.sh   # állapot + napló ellenőrzése
```

**Tipp**: ezekhez a Termux:Widget appon keresztül egy-egy ikont is létrehozhatsz a telefon kezdőképernyőjén, hogy ne kelljen a parancsokat begépelned — l. "Függelék: Widget-ikonok" lent.

## 6. Kézi feltöltés régebbi/kihagyott képekhez

Ha egy kép akkor készült, amikor az automatikus feltöltés ki volt kapcsolva (vagy egy régebbi, korábbi képet szeretnél utólag felküldeni), a telefon **saját Galéria/Fotók appjának natív, bélyegképes, többes kijelöléses** felületét használjuk a kiválasztáshoz — nem kell hozzá semmilyen Termux-beli lista:

1. Nyisd meg a Galéria/Fotók appot, válaszd ki (többes kijelöléssel) a feltöltendő képeket.
2. **Megosztás** → **"Mentés eszközre" / "Másolás ide"** → válaszd ki a **`Pictures/LuminaFeltoltes`** mappát (ha még nem létezik, hozd létre egyszer; ide fogsz mindig menteni, ha kézi feltöltést szeretnél).
3. Ennyi — a háttérben futó figyelő (`lumina_watcher.sh`) ezt a mappát **mindig** figyeli, függetlenül attól, be van-e kapcsolva az automatikus kamera-feltöltés, és pár másodpercen belül automatikusan feltölti az odamentett képeket. Sikeres feltöltés (vagy tudatos kihagyás) után a kép törlődik a telefonról, és egy sor kerül a `feltoltve/feltoltott_kepek.csv` naplóba: időpont, fájlnév, státusz (`feltoltve` / `skip-mar-fent` / `skip-torolve`).

Ha esetleg a figyelő folyamat épp nem futott, amikor odatetted a képeket, kézzel is kiválthatod az utólagos feldolgozást:
```bash
bash ~/lumina_auto_feltoltes/manual_upload.sh
```
(Ehhez is készíthetsz Widget-ikont, l. `shortcuts/Lumina kézi feltöltés.sh`.)

## Ismert korlátok

- A figyelés **valós idejű** (`inotifywait`) — ha a figyelő folyamat véletlenül leáll (pl. Android lekilövi a háttérben), és közben készül egy fotó a kamera-mappában, azt **nem** fogja utólag automatikusan észrevenni, amikor újraindul. Erre való a **6. pont (kézi feltöltés)** — azzal utólag pótolható.
- HEIC-fájlok JPG-vé konvertálása az `imagemagick`-kel történik; ha ez lassú a telefonon, jelezd, más módszert is választhatunk.
- A `clean_string()` névtisztítás bash-ben van megvalósítva (nem Python), a legtöbb esetben ugyanazt az eredményt adja, mint a PC-s eszközök, de nagyon egzotikus fájlnevek esetén apró eltérés előfordulhat.
- **Termux:Widget ismert probléma**: ha a `~/.shortcuts/`-ba másolt scriptek nem jelennek meg a widgetben (üres lista, hibaüzenet nélkül), ennek szinte biztosan az az oka, hogy a Termux és a Termux:Widget **nem ugyanarról a forrásból** lett telepítve — töröld mindkettőt, és telepítsd újra egymás után, ugyanarról az F-Droid oldalról. Eddig ez a probléma nálunk megoldatlan maradt, a fő funkció (feltöltés) enélkül is működik, csak a be/kikapcsolás egyelőre parancssorból (vagy SSH-n) történik.
- Az `upload_lib.sh`-ban a `LUMINA_SERVER` változó a **tablet** Tailscale-címére van beállítva (`100.67.27.6:8000`) — ha ez a cím megváltozna (pl. a tablet Tailscale-ből törlődik és újracsatlakozik), ezt a sort kézzel frissíteni kell a scriptben.

---

## Függelék: SSH hozzáférés (opcionális, de ajánlott a további fejlesztéshez)

Ha SSH-t állítasz be a telefonon, a jövőbeli frissítések (új script-verziók) közvetlenül a PC-ről telepíthetők `scp`-vel, a Google Drive-os kerülő út nélkül.

1. Telepítsd az **openssh** csomagot, és indítsd el az SSH szervert:
   ```bash
   pkg install openssh
   sshd
   ```
   Alapból a **8022**-es porton figyel. A felhasználóneved az `whoami` paranccsal derül ki (jellemzően `u0_a...` formátumú).
2. Add meg a PC nyilvános kulcsát (ha a fejlesztő oldalán már létezik egy), hogy jelszó nélkül, kulcs-alapú hitelesítéssel lehessen csatlakozni:
   ```bash
   mkdir -p ~/.ssh
   echo "<ide a nyilvanos kulcs>" >> ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```
3. Automatikus indítás újraindítás után: `start-sshd.sh` bemásolása a `~/.termux/boot/` mappába (ugyanúgy, mint a 3. pontban a figyelő-indító scriptnél):
   ```bash
   cp ~/lumina_auto_feltoltes/start-sshd.sh ~/.termux/boot/
   chmod +x ~/.termux/boot/start-sshd.sh
   ```

Ezután a PC-ről: `ssh -p 8022 <felhasznalonev>@<telefon-tailscale-cime>`.

## Függelék: Widget-ikonok (Termux:Widget)

1. Telepítsd a **Termux:Widget** appot F-Droid-ról, **ugyanarról a forrásról**, mint a fő Termux appot (l. "Ismert korlátok" a widget-kompatibilitási problémáról).
2. Nyisd meg egyszer (üres ablak, de kell az induláshoz).
3. Másold be a `shortcuts/` mappa tartalmát a telefonon a `~/.shortcuts/` mappába, és tedd futtathatóvá:
   ```bash
   mkdir -p ~/.shortcuts
   cp ~/lumina_auto_feltoltes_forras/shortcuts/*.sh ~/.shortcuts/
   chmod +x ~/.shortcuts/*.sh
   ```
   (Cseréld ki az útvonalat arra, ahonnan a `shortcuts/` mappát átmásoltad - pl. SSH-nál közvetlenül `~/.shortcuts/`-ba is másolhatod.)
4. A telefon kezdőképernyőjén: hosszan nyomás egy üres területen → **Widgetek** → **Termux:Widget** → húzd ki a kezdőképernyőre. A widget ekkor listázza a `~/.shortcuts/`-ban lévő scripteket, és rájuk koppintva lefuttatja őket.
