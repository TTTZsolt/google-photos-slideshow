"""Regresszios tesztek a Lomtar (backend/routers/trash.py) logikajahoz.

Nem er hozza az eles adatbazishoz es a B2-hoz: memoriabeli SQLite + hamis B2 kliens.
Futtatas a projekt gyokerebol:   python -m pytest tests -q
(Fuggosegek: requirements.txt + pytest. Ha egy Windows alkalmazas-vezerlesi szabaly
blokkolja a SQLAlchemy natív DLL-jét, a "sqlalchemy<2.1" tiszta-Python tartalekra esik vissza.)

Fo vedett hiba (2026-09): a Lomtar urites elavult media_items.id-val probalt torolni
-> "File not present" -> a fizikai fajl arvan ottmaradt, az adatbazis-sor viszont torlodott.
"""
import csv
import itertools
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from b2sdk.v2.exception import FileNotPresent

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models  # noqa: E402
from backend.database import Base  # noqa: E402
from backend.routers import trash  # noqa: E402

LIVE, TRASH = "kepek02", "torles-elott"
_ids = itertools.count(1)


class FakeVersion:
    def __init__(self, id_, sha1):
        self.id_ = id_
        self.content_sha1 = sha1


class FakeBucket:
    def __init__(self, fake, name):
        self.fake, self.name = fake, name

    def get_file_info_by_name(self, file_name):
        if self.fake.fail_lookup:
            raise RuntimeError("network down")
        entry = self.fake.buckets.get(self.name, {}).get(file_name)
        if not entry:
            raise FileNotPresent(file_name)
        return FakeVersion(*entry)


class FakeB2State:
    def __init__(self):
        self.buckets = {LIVE: {}, f"{LIVE}-thumbs": {}, TRASH: {}, f"{TRASH}-thumbs": {}}
        self.fail_lookup = False
        self.fail_delete = False
        self.fail_move = False


def make_client_class(state):
    class _Client:
        def __init__(self, key_id=None, app_key=None):
            self.b2_api = self

        def get_bucket_by_name(self, name):
            return FakeBucket(state, name)

        def delete_file_version(self, bucket, file_name, file_id):
            if state.fail_delete:
                raise RuntimeError("b2 throttled")
            entry = state.buckets.get(bucket, {}).get(file_name)
            # Pontosan mint a valodi B2: csak a kozvetlenul mostani id torolheto.
            if not entry or entry[0] != file_id:
                raise FileNotPresent(f"{file_name} id={file_id}")
            del state.buckets[bucket][file_name]
            return True

        def move_file(self, src, dst, file_name, file_info=None, dest_file_name=None):
            if state.fail_move:
                raise RuntimeError("b2 move failed")
            entry = state.buckets.get(src, {}).get(file_name)
            if not entry:
                raise FileNotPresent(file_name)
            new_id = f"new-{next(_ids)}"
            state.buckets[dst][dest_file_name or file_name] = (new_id, entry[1])
            del state.buckets[src][file_name]
            return FakeVersion(new_id, entry[1])

    return _Client


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    state = FakeB2State()
    monkeypatch.setattr(trash, "SessionLocal", Session)
    monkeypatch.setattr(trash, "B2Client", make_client_class(state))
    csv_path = tmp_path / "deleted_sha1_list.csv"
    monkeypatch.setattr(trash, "DELETED_SHA1_CSV", str(csv_path))

    app = FastAPI()
    app.include_router(trash.router)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[trash.get_db] = _get_db

    s = Session()
    s.add(models.B2Account(id=1, key_id="k", application_key="a", bucket_name=LIVE,
                           trash_bucket_name=TRASH, is_active=True))
    s.commit()
    s.close()

    class Env:
        pass

    e = Env()
    e.Session, e.state, e.client, e.csv = Session, state, TestClient(app), csv_path
    return e


def add_trashed(env, name, sha1, stale_id="OLD-ID"):
    """Egy "Lomtarba tett" kep: a fajl a Lomtar vodorben UJ id-val van (masolas utan),
    az adatbazis viszont a regi id-t orzi - pont ez a valos allapot."""
    env.state.buckets[TRASH][name] = (f"real-{next(_ids)}", sha1)
    env.state.buckets[f"{TRASH}-thumbs"][name] = (f"thumb-{next(_ids)}", "t" + sha1)
    s = env.Session()
    s.add(models.MediaItem(id=stale_id + name, b2_account_id=1, bucket_name=TRASH, file_name=name,
                           sha1=sha1, is_in_sorter=False))
    s.add(models.MediaClassification(file_name=name, is_deleted=True))
    s.commit()
    s.close()


def counts(env):
    s = env.Session()
    try:
        return (s.query(models.MediaItem).count(),
                s.query(models.MediaClassification).count(),
                s.query(models.DeletedContentHash).count())
    finally:
        s.close()


def csv_sha1s(env):
    if not env.csv.exists():
        return []
    with open(env.csv, newline="", encoding="utf-8") as f:
        return [r["sha1"] for r in csv.DictReader(f)]


# ---------------------------------------------------------------- Lomtar urites

def test_empty_trash_deletes_physically_despite_stale_id(env):
    add_trashed(env, "2015/06/a.jpg", "sha-a")
    add_trashed(env, "2015/06/b.jpg", "sha-b")

    r = env.client.post("/api/trash/empty")
    assert r.status_code == 200

    assert env.state.buckets[TRASH] == {}, "a fizikai fajl nem torlodott (arva maradt)"
    assert env.state.buckets[f"{TRASH}-thumbs"] == {}
    assert counts(env) == (0, 0, 2)
    assert sorted(csv_sha1s(env)) == ["sha-a", "sha-b"]


def test_empty_trash_keeps_rows_when_physical_delete_fails(env):
    add_trashed(env, "x.jpg", "sha-x")
    env.state.fail_delete = True

    env.client.post("/api/trash/empty")

    assert "x.jpg" in env.state.buckets[TRASH]
    mi, mc, _ = counts(env)
    assert (mi, mc) == (1, 1), "a sor nem maradt meg, pedig a fajl meg a Lomtarban van"


def test_empty_trash_keeps_rows_when_lookup_fails(env):
    add_trashed(env, "x.jpg", "sha-x")
    env.state.fail_lookup = True

    env.client.post("/api/trash/empty")

    assert counts(env)[:2] == (1, 1)
    assert "x.jpg" in env.state.buckets[TRASH]


def test_empty_trash_removes_rows_when_file_already_gone(env):
    add_trashed(env, "gone.jpg", "sha-g")
    env.state.buckets[TRASH].clear()  # a B2-n mar nincs

    env.client.post("/api/trash/empty")

    assert counts(env)[:2] == (0, 0)


def test_failed_item_does_not_block_the_rest(env):
    add_trashed(env, "ok.jpg", "sha-ok")
    add_trashed(env, "bad.jpg", "sha-bad")
    real_delete = trash.B2Client.delete_file_version

    def selective(self, bucket, name, fid):
        if name == "bad.jpg":
            raise RuntimeError("boom")
        return real_delete(self, bucket, name, fid)

    trash.B2Client.delete_file_version = selective
    env.client.post("/api/trash/empty")

    assert "ok.jpg" not in env.state.buckets[TRASH]
    assert "bad.jpg" in env.state.buckets[TRASH]
    assert counts(env)[:2] == (1, 1)


# ---------------------------------------------------------------- Visszaallitas

def _tombstone(env, sha1, name):
    s = env.Session()
    s.add(models.DeletedContentHash(sha1=sha1, last_known_file_name=name, reason="trash-empty"))
    s.commit()
    s.close()
    trash.append_deleted_sha1_csv(sha1, name, "trash-empty")


def test_restore_removes_tombstone(env):
    add_trashed(env, "r.jpg", "sha-r")
    _tombstone(env, "sha-r", "r.jpg")
    _tombstone(env, "sha-other", "other.jpg")

    s = env.Session()
    item_id = s.query(models.MediaItem).first().id
    s.close()
    r = env.client.post(f"/api/trash/restore/{item_id}")
    assert r.status_code == 200, r.text

    assert "r.jpg" in env.state.buckets[LIVE]
    s = env.Session()
    assert [t.sha1 for t in s.query(models.DeletedContentHash)] == ["sha-other"]
    s.close()
    assert csv_sha1s(env) == ["sha-other"]


def test_restore_all_success_removes_tombstones_and_updates_ids(env):
    add_trashed(env, "a.jpg", "sha-a")
    add_trashed(env, "b.jpg", "sha-b")
    _tombstone(env, "sha-a", "a.jpg")
    _tombstone(env, "sha-b", "b.jpg")

    r = env.client.post("/api/trash/restore-all")
    assert r.status_code == 200

    assert set(env.state.buckets[LIVE]) == {"a.jpg", "b.jpg"}
    s = env.Session()
    assert s.query(models.DeletedContentHash).count() == 0
    for mi in s.query(models.MediaItem):
        assert mi.bucket_name == LIVE and mi.id.startswith("new-")
    assert s.query(models.MediaClassification).filter_by(is_deleted=True).count() == 0
    s.close()
    assert csv_sha1s(env) == []


def test_restore_all_failure_reverts_db_state(env):
    add_trashed(env, "a.jpg", "sha-a")
    _tombstone(env, "sha-a", "a.jpg")
    env.state.fail_move = True

    env.client.post("/api/trash/restore-all")

    assert "a.jpg" in env.state.buckets[TRASH]
    s = env.Session()
    mc = s.query(models.MediaClassification).one()
    mi = s.query(models.MediaItem).one()
    assert mc.is_deleted is True, "a fajl meg a Lomtarban van, az adatbazis mar 'elo'-nek mondja"
    assert mi.is_in_sorter is False and mi.bucket_name == TRASH
    assert s.query(models.DeletedContentHash).count() == 1, "sikertelen visszaallitasnal a tombstone maradjon"
    s.close()
    assert csv_sha1s(env) == ["sha-a"]
