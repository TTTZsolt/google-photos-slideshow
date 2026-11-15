"""A felvetel idejenek (creation_time) meghatarozasa a B2 fajlnevbol.

A B2-szinkron nem tud EXIF-et olvasni (az letoltest igenyelne), de a fajl
utvonala es neve hordozza a datumot:

* Takeout-feltolto:  ``EEEE/HH/NN-album/fajlnev.jpg`` (vagy ``EEEE/HH/fajlnev.jpg``)
* Telefonos feltoltes: ``EEEE/HH/tisztitott-nev.jpg`` (nincs napi mappa)

Az utvonal ev/honapja megbizhato (a feltolto eszkoz EXIF -> Takeout JSON ->
fajlnev sorrendben szamolta), a fajlnev adja a nap pontos idejet.

Az idok HELYI (naiv) datetime-ok, mint a kod tobbi reszeben.
"""
import re
from datetime import datetime
from typing import Optional, Tuple

# A fajlnevek tisztitva vannak (clean_string): "IMG_20211224_181930" -> "img-20211224-181930"
_FILENAME_DATETIME_RE = re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})[-_](\d{2})(\d{2})(\d{2})")
_FILENAME_DATE_RE = re.compile(r"(?<!\d)(\d{4})[-_]?(\d{2})[-_]?(\d{2})(?!\d)")
_DAY_FOLDER_RE = re.compile(r"^(\d{2})(?:-|$)")

MIN_YEAR = 1995

PRECISION_EXACT = "exact"  # datum + ido (fajlnevbol, az utvonallal egyezo)
PRECISION_DAY = "day"      # csak a nap (napi mappabol vagy datum-only fajlnevbol)
PRECISION_NONE = None      # nincs megbizhato datum


def _parse_path(file_name: str) -> Optional[Tuple[int, int, Optional[int]]]:
    """(ev, honap, nap_vagy_None) az utvonalbol, vagy None, ha nem ertelmezheto."""
    if not file_name:
        return None
    parts = file_name.replace("\\", "/").split("/")
    if len(parts) < 3:  # kell legalabb ev/honap/fajl
        return None
    if not (len(parts[0]) == 4 and parts[0].isdigit() and len(parts[1]) == 2 and parts[1].isdigit()):
        return None
    year, month = int(parts[0]), int(parts[1])
    if not (MIN_YEAR <= year <= datetime.now().year + 1 and 1 <= month <= 12):
        return None
    day = None
    if len(parts) >= 4:  # parts[2] mappa (nem a fajlnev)
        m = _DAY_FOLDER_RE.match(parts[2])
        if m:
            d = int(m.group(1))
            if 1 <= d <= 31:
                day = d
    return year, month, day


def _filename_datetime(base: str):
    """(datetime, van_ido) a fajlnevbol, vagy None."""
    m = _FILENAME_DATETIME_RE.search(base)
    if m:
        try:
            y, mo, d, h, mi, s = (int(g) for g in m.groups())
            return datetime(y, mo, d, h, mi, s), True
        except ValueError:
            pass
    m = _FILENAME_DATE_RE.search(base)
    if m:
        try:
            y, mo, d = (int(g) for g in m.groups())
            return datetime(y, mo, d), False
        except ValueError:
            pass
    return None


def derive_capture_date(file_name: str) -> Tuple[Optional[datetime], Optional[str]]:
    """(datetime, pontossag) a felvetel idejerol, az utvonalbol es a fajlnevbol.

    Szabalyok:
    1. A fajlnevi datum csak akkor szamit, ha egyezik az utvonal evevel es
       honapjaval (es napjaval, ha az utvonal a napot is tartalmazza) -
       kulonben az utvonal az iranyado.
    2. Ha az utvonal a napot is tartalmazza, de a fajlnev nem segit: az adott nap, 00:00.
    3. Csak ev/honap ismert, a fajlnev nem segit: (None, None) - kimarad a szurobol.
    """
    path = _parse_path(file_name)
    if path is None:
        return None, None
    year, month, day = path

    base = file_name.replace("\\", "/").split("/")[-1]
    fn = _filename_datetime(base)
    if fn is not None:
        dt, has_time = fn
        if dt.year == year and dt.month == month and (day is None or dt.day == day):
            return dt, (PRECISION_EXACT if has_time else PRECISION_DAY)

    if day is not None:
        try:
            return datetime(year, month, day), PRECISION_DAY
        except ValueError:
            pass
    return None, None


def resolve_creation_time(file_name: str, existing: Optional[datetime]) -> Optional[datetime]:
    """A `creation_time` vegso erteke egy fajlhoz a szinkron/javitas soran.

    A B2 feltoltesi idot SOHA nem hasznaljuk. A meglevo (pl. a telefonos
    feldolgozo altal EXIF-bol beirt) erteket megtartjuk, ha az utvonallal
    osszefer - ez nem veszi el egy pontosabb, mar tarolt idot.
    """
    derived, precision = derive_capture_date(file_name)
    path = _parse_path(file_name)

    if precision == PRECISION_EXACT:
        return derived
    if precision == PRECISION_DAY:
        if existing is not None and existing.date() == derived.date():
            return existing  # ugyanaz a nap, de a tarolt ertek ido-pontos
        return derived
    # Nincs megbizhato datum a fajlnevbol/utvonalbol: a meglevo marad, ha egyezik az ev/honappal
    if existing is not None and path is not None and (existing.year, existing.month) == path[:2]:
        return existing
    return None
