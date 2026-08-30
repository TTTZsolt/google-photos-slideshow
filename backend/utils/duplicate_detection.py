from io import BytesIO
from PIL import Image


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


def group_near_duplicates(hashes: list[tuple[str, int]], threshold: int = 10) -> list[list[str]]:
    """
    hashes: list of (filename, dhash), already sorted by filename - for typical
    camera/phone naming this also means sorted by capture time, so burst shots of
    the same moment end up as neighbours in the list.

    Only compares each item to its immediate predecessor (not every pair), so two
    unrelated but visually similar photos elsewhere in the library never merge just
    because they happen to look alike - only an actual consecutive run does.

    Returns a list of groups; images with no near-duplicate neighbour come back as
    their own 1-item group.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    prev_hash = None
    for fname, h in hashes:
        if current and prev_hash is not None and hamming_distance(prev_hash, h) <= threshold:
            current.append(fname)
        else:
            if current:
                groups.append(current)
            current = [fname]
        prev_hash = h
    if current:
        groups.append(current)
    return groups
