"""Unit tests for the run store: snapshots, redaction, migrations, replay of refusals (F5e)."""

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from aimpire.cognition.budget import Caps
from aimpire.persistence import snapshot
from aimpire.persistence.blobs import REDACTED, BlobStore, redact
from aimpire.persistence.db import check_sqlite_version, migrations
from aimpire.persistence.store import ReplayMismatch, RunStore, verify_replay
from aimpire.sim.hashing import state_hash
from tests.acceptance.test_f5e_council import (
    MONTH,
    PRICE,
    SEED,
    _create,
    _drive,
    _Priced,
    _seats_for,
    _world,
)


def test_snapshot_round_trip_keeps_the_hash():
    state, _ = _world()
    state.layers["food"][1, 2] = 2**40
    state.carries["food"][3, 3] = 7
    state.tick = 33
    restored = snapshot.from_value(snapshot.to_value(state))
    assert state_hash(restored) == state_hash(state)
    assert restored.layers["food"].dtype == np.int64
    with pytest.raises(TypeError):
        snapshot.from_value(
            {**snapshot.to_value(state), "layers": {"food": {"shape": [1, 1], "data": [1.5]}}}
        )
    with pytest.raises(ValueError):
        snapshot.from_value({"format": "other"})


def test_redact_removes_keys_and_key_shapes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MY_SERVICE_TOKEN", "tok-1234567890")
    monkeypatch.setenv("SHORT_API_KEY", "abc")  # too short to be a credential: left alone
    text = (
        'use tok-1234567890 and sk-or-v1-abcdef123 "Bearer xyz.789" '
        "https://user:pass@example.org abc"
    )
    out = redact(text)
    for leaked in ("tok-1234567890", "sk-or-v1", "xyz.789", "user:pass"):
        assert leaked not in out
    assert out.count(REDACTED) == 4
    assert '"Bearer ' in out and out.endswith(" abc")  # quotes kept: JSON stays valid


def test_blobs_are_content_addressed_and_checked(tmp_path: Path):
    blobs = BlobStore(tmp_path / "blobs")
    first = blobs.put({"b": 1, "a": [1, 2]})
    assert blobs.put({"a": [1, 2], "b": 1}) == first
    assert blobs.get(first) == {"a": [1, 2], "b": 1}
    with pytest.raises(ValueError):
        blobs.get("../../etc/passwd")


def test_sqlite_version_floor_and_migrations():
    check_sqlite_version((3, 51, 3))
    with pytest.raises(RuntimeError, match="too old"):
        check_sqlite_version((3, 51, 2))
    assert [n for n, _ in migrations()] == [1]


def test_create_refuses_an_existing_run_and_a_mismatched_replay(tmp_path: Path):
    store = _create(tmp_path, "r1")
    assert store.manifest()["seed"] == SEED and store.manifest()["schema_version"] == 1
    with pytest.raises(FileExistsError):
        _create(tmp_path, "r1")
    with pytest.raises(ValueError, match="original seed"):
        RunStore.create(
            tmp_path / "r2",
            run_id="r2",
            seed=SEED + 1,
            rules_version="v1",
            rules_hash="rules-hash",
            caps=Caps(),
            month=MONTH,
            replay_of=store,
        )
    with pytest.raises(ValueError, match="YYYY-MM"):
        RunStore.create(
            tmp_path / "r3",
            run_id="r3",
            seed=SEED,
            rules_version="v1",
            rules_hash="rules-hash",
            caps=Caps(),
            month="2026-13",
        )
    store.close()
    reader = RunStore.open(tmp_path / "r1", read_only=True)
    with pytest.raises(sqlite3.OperationalError):
        reader.checkpoint(_world()[0], "periodic")
    reader.close()


def test_budget_refusals_replay_as_refusals(tmp_path: Path):
    state, entity_ids = _world()
    prices = {"C1": PRICE, "C2": PRICE}
    original = _create(tmp_path, "paid", caps=Caps(run_micro_usd=1_000_000))
    seats = _seats_for({"C1": _Priced(600_000), "C2": _Priced(600_000)}, entity_ids, prices)
    _drive(state, 25, seats, original.budget_guard(0), original)
    outcomes = [row["outcome"] for row in original.decisions()]
    # Each council reserves 600,000 twice against a 1,000,000 cap: one seat waits every time.
    assert outcomes.count("BUDGET") == 3 and outcomes.count("VALID") == 3

    replay_state, replay_ids = _world()
    replay = _create(tmp_path, "paid-replay", replay_of=original)
    recorded = original.recorded_provider()
    seats = _seats_for({"C1": recorded, "C2": recorded}, replay_ids, prices)
    _drive(replay_state, 25, seats, original.replay_gate(), replay)
    verify_replay(original, replay)
    assert [r["outcome"] for r in replay.decisions()] == outcomes
    assert replay.run_spent() == 0  # replaying costs nothing
    assert state_hash(replay.load_checkpoint(-1 + len(replay.checkpoints()))) == state_hash(
        replay_state
    )


def test_verify_replay_reports_a_short_replay(tmp_path: Path):
    state, entity_ids = _world()
    original = _create(tmp_path, "a")
    _drive(state, 20, _seats_for({}, entity_ids), original.budget_guard(0), original)
    short_state, _ = _world()
    short = _create(tmp_path, "b", replay_of=original)
    _drive(short_state, 10, _seats_for({}, entity_ids), original.replay_gate(), short)
    with pytest.raises(ReplayMismatch):
        verify_replay(original, short)
