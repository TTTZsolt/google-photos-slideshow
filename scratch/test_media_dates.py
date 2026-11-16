"""Egyszeru assert-alapu teszt a backend/utils/media_dates.py-hoz.
Futtatas a projekt gyokerebol:  python scratch/test_media_dates.py
"""
import importlib.util
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("media_dates", os.path.join(ROOT, "backend", "utils", "media_dates.py"))
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

derive = md.derive_capture_date
resolve = md.resolve_creation_time
dt = datetime

# --- derive_capture_date ---
# Telefon: ev/honap/tisztitott-nev, datum+ido a fajlnevben
assert derive("2026/11/img-20261105-143022.jpg") == (dt(2026, 11, 5, 14, 30, 22), "exact")
assert derive("2026/11/20261105-143022.jpg") == (dt(2026, 11, 5, 14, 30, 22), "exact")
# Pixel: 9 jegyu idoresz (HHMMSSmmm) - az elso 6 szamit
assert derive("2026/11/pxl-20261105-143022123.jpg") == (dt(2026, 11, 5, 14, 30, 22), "exact")
# Takeout, napi mappaval + fajlnevi datum (egyezik)
assert derive("2017/06/08-dune-fro/20170608-211651-0.jpg") == (dt(2017, 6, 8, 21, 16, 51), "exact")
# Takeout, napi mappa, a fajlnev nem segit -> a nap, 00:00
assert derive("2017/06/08-dune-fro/img-0123.jpg") == (dt(2017, 6, 8), "day")
# Fajlnevi datum eltér az utvonaltol -> az utvonal az iranyado
assert derive("2017/06/08-dune-fro/20150101-101010.jpg") == (dt(2017, 6, 8), "day")
# A fajlnevi datum honapja eltér, nincs napi mappa -> nincs datum
assert derive("2017/06/20150101-101010.jpg") == (None, None)
# Csak ev/honap, a fajlnev nem segit -> nincs datum (kimarad a szurobol)
assert derive("2017/06/img-0123.jpg") == (None, None)
# Datum-only fajlnev (nincs ido), az utvonallal egyezik
assert derive("2021/08/2021-08-05.jpg") == (dt(2021, 8, 5), "day")
# Ertelmezhetetlen utvonal
assert derive("kep.jpg") == (None, None)
assert derive("valami/mappa/kep.jpg") == (None, None)
assert derive("2026/13/img-20261305-143022.jpg") == (None, None)  # 13. honap
assert derive("1800/01/x.jpg") == (None, None)
assert derive("") == (None, None)
# Ervenytelen datum a fajlnevben (nov 31)
assert derive("2026/11/img-20261131-143022.jpg") == (None, None)
# Visszaperjeles (Windows) utvonal is mukodik
assert derive("2026\\11\\img-20261105-143022.jpg") == (dt(2026, 11, 5, 14, 30, 22), "exact")
# Szam-folyam nem tevesztheto ossze datummal
assert derive("2026/11/img-1234567890-123456.jpg") == (None, None)

# --- resolve_creation_time ---
upload = dt(2026, 11, 6, 9, 0, 0)  # a regi (hibas) ertek tipikus pelda
# Pontos fajlnevi ido felulirja a (hibas) feltoltesi idot
assert resolve("2026/11/img-20261105-143022.jpg", upload) == dt(2026, 11, 5, 14, 30, 22)
# Takeout, csak ev/honap: a regi feltoltesi ido NEM egyezik az utvonallal -> None
assert resolve("2017/06/img-0123.jpg", upload) is None
# Takeout, nap ismert: a nap, mert a feltoltesi ido masik napon van
assert resolve("2017/06/08-dune/img-0123.jpg", upload) == dt(2017, 6, 8)
# Nap ismert es a tarolt ertek ido-pontos ugyanarra a napra -> megmarad
exif = dt(2017, 6, 8, 18, 5, 0)
assert resolve("2017/06/08-dune/img-0123.jpg", exif) == exif
# Telefon, a fajlnev nem segit, de a tarolt (EXIF-es) ertek egyezik az ev/honappal -> megmarad
exif2 = dt(2026, 11, 5, 14, 30, 22)
assert resolve("2026/11/img-0123.jpg", exif2) == exif2
# Nincs meglevo ertek es nincs datum -> None
assert resolve("2026/11/img-0123.jpg", None) is None
# Ertelmezhetetlen utvonal: a meglevo ertek sem marad (nincs mihez viszonyitani)
assert resolve("kep.jpg", upload) is None

print("Minden teszt rendben (media_dates).")
