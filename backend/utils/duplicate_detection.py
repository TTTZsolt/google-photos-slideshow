import os
import re
from datetime import datetime
from io import BytesIO
from PIL import Image

FILENAME_DATETIME_RE = re.compile(r"(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})")


def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> int:
    """8x8 difference-hash (dHash): a cheap perceptual fingerprint. Minor pixel/
    compression differences between near-identical burst shots barely move it,
    unlike a byte-level SHA1 (which flips completely on the smallest change)."""
    img = Image.open(BytesIO(image_bytes)).convert("L").resize(
        (hash_size + 1, hash_size), Image.LANCZOS
    )
    pixels = list(img.getdata())
    bits = 0
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for col in range(hash_size):
            bits = (bits << 1) | int(pixels[row_start + col] > pixels[row_start + col + 1])
    return bits


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def parse_capture_time_from_filename(filename: str):
    """Best-effort YYYYMMDD[_-]HHMMSS extraction from a filename (matches common
    camera/phone naming conventions, e.g. "20210116-135802.jpg"). Returns None if
    no such pattern is found - e.g. purely numeric epoch-millisecond names, or
    generic camera counters like IMG_1234.jpg."""
    base = os.path.splitext(os.path.basename(filename))[0]
    m = FILENAME_DATETIME_RE.search(base)
    if not m:
        return None
    try:
        y, mo, d, h, mi, s = (int(g) for g in m.groups())
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None


def group_near_duplicates(
    hashes: list[tuple[str, int]],
    threshold: int = 10,
    loose_threshold: int = 28,
    max_time_gap_seconds: int = 15,
) -> list[list[str]]:
    """
    hashes: list of (filename, dhash), already sorted by filename - for typical
    camera/phone naming this also means sorted by capture time, so burst shots of
    the same moment end up as neighbours in the list.

    Only compares each item to its immediate predecessor (not every pair), so two
    unrelated but visually similar photos elsewhere in the library never merge just
    because they happen to look alike - only an actual consecutive run does.

    Two-tier match against the previous item in sequence:
      - hamming <= threshold: always grouped. Safe default, works even when neither
        filename carries a parseable timestamp.
      - threshold < hamming <= loose_threshold: grouped ONLY if both filenames carry
        a parseable capture time within max_time_gap_seconds of each other. dHash is
        not shift-invariant - a small camera pan/handshake between two shots of the
        same static subject (e.g. a statue) can push the distance well past a tight
        threshold even though the photos are genuine near-duplicates. Requiring a
        very close capture time before trusting the looser visual match keeps this
        from merging unrelated-but-similar-looking photos taken at different times.

    Returns a list of groups; images with no near-duplicate neighbour come back as
    their own 1-item group.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    prev_hash = None
    prev_fname = None
    for fname, h in hashes:
        matched = False
        if current and prev_hash is not None:
            dist = hamming_distance(prev_hash, h)
            if dist <= threshold:
                matched = True
            elif dist <= loose_threshold:
                t_prev = parse_capture_time_from_filename(prev_fname)
                t_cur = parse_capture_time_from_filename(fname)
                if t_prev is not None and t_cur is not None:
                    if abs((t_cur - t_prev).total_seconds()) <= max_time_gap_seconds:
                        matched = True

        if matched:
            current.append(fname)
        else:
            if current:
                groups.append(current)
            current = [fname]
        prev_hash = h
        prev_fname = fname
    if current:
        groups.append(current)
    return groups
