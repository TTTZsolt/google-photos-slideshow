"""Egyszeri javitas: a media_items.creation_time ujraszamolasa a fajl utvonalabol/nevebol.

A regi szinkron a B2 FELTOLTESI idot irta a creation_time-ba (es felulirta a telefonos
feldolgozo altal beirt pontos idot is). Ez a szkript ugyanazt a szabalyt alkalmazza a
meglevo sorokra, mint a javitott worker.py (backend/utils/media_dates.resolve_creation_time).

Alapertelmezett: DRY-RUN (csak olvas, nem ir semmit). Valos iraskor: --apply
(elotte automatikus biztonsagi masolat az adatbazisrol).

Hasznalat (a projekt gyokerebol):
    python scratch/backfill_creation_time.py                    # dry-run, ./photos_app.db
    python scratch/backfill_creation_time.py --db /ut/photos_app.db
    python scratch/backfill_creation_time.py --apply
"""
import argparse
import csv
import importlib.util
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("media_dates", os.path.join(ROOT, "backend", "utils", "media_dates.py"))
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)

RECENT_MONTHS = 3  # ennyi honapnal frissebb utvonal = "friss" (telefonrol erkezo) kep
SQL_FMT = "%Y-%m-%d %H:%M:%S.%f"  # igy tarolja a SQLAlchemy a DateTime ertekeket SQLite-ban


def parse_db_dt(value):
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def months_ago_cutoff(months):
    now = datetime.now()
    y, m = now.year, now.month - months
    while m <= 0:
        m += 12
        y -= 1
    return (y, m)


def main():
    # Windows-konzol (cp1252) ekezetes utvonalaihoz
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(ROOT, "photos_app.db"))
    ap.add_argument("--apply", action="store_true", help="Tenyleges iras (alapbol dry-run)")
    ap.add_argument("--csv", default=os.path.join(ROOT, "scratch", "creation_time_changes.csv"))
    ap.add_argument("--examples", type=int, default=20)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"HIBA: nem letezik az adatbazis: {args.db}")

    from pathlib import Path
    uri = Path(args.db).resolve().as_uri() + ("?mode=rw" if args.apply else "?mode=ro")
    conn = sqlite3.connect(uri, uri=True)
    rows = conn.execute("SELECT id, file_name, creation_time FROM media_items").fetchall()
    print(f"Adatbazis: {args.db}")
    print(f"Sorok: {len(rows)}   Mod: {'APPLY (iras!)' if args.apply else 'DRY-RUN (csak olvas)'}\n")

    recent_cutoff = months_ago_cutoff(RECENT_MONTHS)
    stats = Counter()
    changes = []   # (id, file_name, old_raw, new_dt_or_None, recent)
    for item_id, file_name, raw in rows:
        old = parse_db_dt(raw)
        new = md.resolve_creation_time(file_name, old)
        path = md._parse_path(file_name)
        recent = bool(path and (path[0], path[1]) >= recent_cutoff)
        bucket = "friss" if recent else "regi"

        if (old is None and new is None) or (old is not None and new is not None and old == new):
            stats[(bucket, "valtozatlan")] += 1
            continue
        kind = "kimarad (NULL)" if new is None else ("beallitva (volt NULL)" if old is None else "javitva")
        stats[(bucket, kind)] += 1
        changes.append((item_id, file_name, raw, new, recent))

    print("Osszesites:")
    for bucket in ("friss", "regi"):
        label = f"friss (utvonal az elmult ~{RECENT_MONTHS} honapbol, telefonrol erkezo)" if bucket == "friss" else "regi (Takeout stb.)"
        print(f"  {label}")
        for kind in ("valtozatlan", "javitva", "beallitva (volt NULL)", "kimarad (NULL)"):
            print(f"    {kind:<24} {stats[(bucket, kind)]}")
    print(f"\nValtozo sorok osszesen: {len(changes)}")

    recent_changes = [c for c in changes if c[4]]
    print(f"\nPeldak a FRISS kepekbol (max {args.examples} / {len(recent_changes)}):")
    for item_id, fn, raw, new, _ in recent_changes[: args.examples]:
        print(f"  {fn}\n      elotte: {raw}\n      utana : {new}")
    if not recent_changes:
        print("  (nincs valtozas a friss kepeknel)")

    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "file_name", "elotte", "utana", "friss"])
        for item_id, fn, raw, new, recent in changes:
            w.writerow([item_id, fn, raw, new.strftime(SQL_FMT) if new else "", "igen" if recent else "nem"])
    print(f"\nValtozasok CSV-je: {args.csv}")

    if not args.apply:
        print("\nDRY-RUN: az adatbazisban semmi nem valtozott. Iraashoz: --apply")
        return

    # --- APPLY ---
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{args.db}.backup-before-creation-time-{stamp}"
    print(f"\nBiztonsagi masolat: {backup_path}")
    dst = sqlite3.connect(backup_path)
    conn.backup(dst)
    dst.close()

    updates = [(new.strftime(SQL_FMT) if new else None, item_id) for item_id, _, _, new, _ in changes]
    with conn:
        conn.executemany("UPDATE media_items SET creation_time = ? WHERE id = ?", updates)
    print(f"Frissitett sorok: {len(updates)}")
    conn.close()


if __name__ == "__main__":
    main()
