"""The run store: one SQLite database and one blob folder per run (ADR-0004).

Layout of ``runs/<run_id>/``::

    run.db             manifest, inputs, decisions, checkpoints (migrations/0001_init.sql)
    blobs/<sha>.json.zst  requests, responses and full-state checkpoints

* **inputs** is the replay source of truth: one row per decision, in the order
  it was applied, naming the stored response (or the budget refusal).
* **decisions** is audit and metering: provider, model, outcome, the
  validated record, tokens, latency, and the spend ledger
  (``reserved_micro_usd``, ``charged_micro_usd``, ``month``).
* **checkpoints** hold the state hash, the per-part hashes and a snapshot.

The monthly cap spans runs, but each run has its own database, so
``spend.month_spent`` sums the ledgers of every run under a runs folder.

Nothing secret is written: every blob and JSON column goes through
``blobs.redact`` first. The manifest records versions, never the environment.
"""

import json
import platform
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import numpy as np

from aimpire.cognition.budget import BudgetGuard, Caps, RecordedRefusals, Refusal
from aimpire.cognition.council import Settled
from aimpire.cognition.offline import RecordedProvider
from aimpire.cognition.recording import result_to_record
from aimpire.contracts.mind import CONTRACT_VERSION
from aimpire.persistence import snapshot
from aimpire.persistence.blobs import BlobStore, canonical_json
from aimpire.persistence.db import connect, migrate
from aimpire.persistence.replay import ReplayMismatch, verify_replay
from aimpire.persistence.spend import DB_NAME, check_month, current_month, month_spent
from aimpire.sim import hashing, rng
from aimpire.sim.state import WorldState

__all__ = ["ReplayMismatch", "RunStore", "month_spent", "verify_replay"]


class RunStore:
    """Read and write one run's database. Implements the runner's ``CouncilSink``."""

    def __init__(self, run_dir: Path, db: sqlite3.Connection, month: str) -> None:
        self.run_dir = run_dir
        self._db = db
        self.blobs = BlobStore(run_dir / "blobs")
        self.month = check_month(month)
        self.run_id: str = self.manifest()["run_id"]

    # --- opening -------------------------------------------------------------

    @classmethod
    def create(  # noqa: PLR0913 (the manifest's fields)
        cls,
        run_dir: Path,
        *,
        run_id: str,
        seed: int,
        rules_version: str,
        rules_hash: str,
        caps: Caps,
        month: str | None = None,
        replay_of: RunStore | None = None,
        config: Mapping[str, Any] | None = None,
        code_version: str = "",
    ) -> RunStore:
        """Create a new run database. Fails if ``run_dir`` already holds one."""
        month = check_month(month or current_month())
        if replay_of is not None:
            source = replay_of.manifest()
            if (source["seed"], source["rules_version"], source["rules_hash"]) != (
                seed,
                rules_version,
                rules_hash,
            ):
                raise ValueError("a recorded replay needs the original seed and rules")
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / DB_NAME
        if path.exists():
            raise FileExistsError(f"{path} already exists")
        db = connect(path, read_only=False)
        version = migrate(db)
        row = {
            "run_id": run_id,
            "schema_version": version,
            "created_month": month,
            "seed": str(seed),
            "rules_version": rules_version,
            "rules_hash": rules_hash,
            "contract": CONTRACT_VERSION,
            "state_format": hashing.FORMAT,
            "draw_version": rng.VERSION,
            "replay_of_run_id": replay_of.run_id if replay_of is not None else None,
            "run_cap_micro_usd": caps.run_micro_usd,
            "monthly_cap_micro_usd": caps.monthly_micro_usd,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "sqlite_version": sqlite3.sqlite_version,
            "code_version": code_version,
            "config_json": canonical_json(dict(config or {})),
        }
        with db:
            names = ", ".join(row)
            marks = ", ".join(f":{name}" for name in row)
            db.execute(f"INSERT INTO manifest ({names}) VALUES ({marks})", row)
        return cls(run_dir, db, month)

    @classmethod
    def open(cls, run_dir: Path, *, read_only: bool = False, month: str | None = None) -> RunStore:
        """Open an existing run. New spend is booked to ``month`` (default: now, UTC)."""
        path = run_dir / DB_NAME
        if not path.exists():
            raise FileNotFoundError(path)
        db = connect(path, read_only=read_only)
        if not read_only:
            migrate(db)
        return cls(run_dir, db, month or current_month())

    def close(self) -> None:
        """Close the database (and fold the WAL back into it)."""
        self._db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: type[BaseException] | BaseException | TracebackType | None) -> None:
        self.close()

    # --- writing (CouncilSink) ----------------------------------------------

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        """Store one council's decisions, in the order they were applied."""
        with self._db:
            for item in settled:
                self._record(tick, council, item)

    def _record(self, tick: int, council: int, item: Settled) -> None:
        call, result = item.call, item.result
        req = call.request
        identity = call.provider.describe()
        request_blob = self.blobs.put(
            {
                "decision_id": req.decision_id,
                "civ_id": req.civ_id,
                "contract": req.contract,
                "system": req.system,
                "observation": req.observation.model_dump(mode="json"),
                "observation_text": req.observation_text,
                "max_output_tokens": req.max_output_tokens,
                "timeout_s": repr(req.timeout_s),  # audit only; kept as text, never a float
                "effort": req.effort,
                "temperature": None if req.temperature is None else repr(req.temperature),
            }
        )
        response_blob = self.blobs.put(result_to_record(result)) if result is not None else ""
        refusal = item.grant.refused.value if item.grant.refused is not None else ""
        payload = {
            "decision_id": req.decision_id,
            "civ_id": req.civ_id,
            "council": council,
            "response_blob": response_blob,
            "refusal": refusal,
        }
        cursor = self._db.execute(
            "INSERT INTO inputs (tick, kind, ref, payload_json) VALUES (?, 'decision', ?, ?)",
            (tick, req.decision_id, canonical_json(payload)),
        )
        usage = result.usage if result is not None else None
        self._db.execute(
            "INSERT INTO decisions VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                req.decision_id,
                cursor.lastrowid,
                tick,
                council,
                req.civ_id,
                identity.provider,
                identity.model,
                identity.digest,
                result.model_reported if result is not None else "",
                result.status if result is not None else "not_called",
                item.record.outcome.value,
                refusal,
                canonical_json(item.record.to_value()),
                request_blob,
                response_blob,
                usage.input_tokens if usage else 0,
                usage.output_tokens if usage else 0,
                usage.reasoning_tokens if usage else 0,
                result.latency_ms if result is not None else 0,
                result.attempts if result is not None else 0,
                item.grant.reserved,
                item.charged,
                self.month,
            ),
        )

    def checkpoint(self, state: WorldState, label: str) -> None:
        """Store the full state, its hash and its per-part hashes."""
        parts = hashing.subsystem_hashes(state)
        blob = self.blobs.put(snapshot.to_value(state))
        with self._db:
            self._db.execute(
                "INSERT INTO checkpoints (tick, label, state_hash, subsystem_hashes_json,"
                " state_blob) VALUES (?, ?, ?, ?, ?)",
                (state.tick, label, hashing.state_hash(state), canonical_json(parts), blob),
            )

    # --- reading ---------------------------------------------------------------

    def manifest(self) -> dict[str, Any]:
        """The manifest row; ``seed`` as an int, ``config`` decoded."""
        cursor = self._db.execute("SELECT * FROM manifest")
        names = [d[0] for d in cursor.description]
        row = dict(zip(names, cursor.fetchone(), strict=True))
        row["seed"] = int(row["seed"])
        row["config"] = json.loads(row.pop("config_json"))
        return row

    def checkpoints(self) -> list[tuple[int, str, str]]:
        """``(tick, label, state_hash)`` for every checkpoint, in the order taken."""
        query = "SELECT tick, label, state_hash FROM checkpoints ORDER BY checkpoint_id"
        return [(int(t), str(lbl), str(h)) for t, lbl, h in self._db.execute(query)]

    def subsystem_hashes(self, index: int) -> dict[str, str]:
        """The per-part hashes of the ``index``-th checkpoint."""
        query = (
            "SELECT subsystem_hashes_json FROM checkpoints ORDER BY checkpoint_id LIMIT 1 OFFSET ?"
        )
        return json.loads(self._db.execute(query, (index,)).fetchone()[0])

    def load_checkpoint(self, index: int) -> WorldState:
        """Restore the state saved at the ``index``-th checkpoint."""
        query = "SELECT state_blob FROM checkpoints ORDER BY checkpoint_id LIMIT 1 OFFSET ?"
        return snapshot.from_value(self.blobs.get(self._db.execute(query, (index,)).fetchone()[0]))

    def decisions(self) -> list[dict[str, Any]]:
        """Every decision row in applied order, with ``record`` decoded."""
        cursor = self._db.execute("SELECT * FROM decisions ORDER BY seq")
        names = [d[0] for d in cursor.description]
        rows = [dict(zip(names, values, strict=True)) for values in cursor]
        for row in rows:
            row["record"] = json.loads(row.pop("record_json"))
        return rows

    def run_spent(self) -> int:
        """Micro-dollars charged by this run."""
        query = "SELECT COALESCE(SUM(charged_micro_usd), 0) FROM decisions"
        return int(self._db.execute(query).fetchone()[0])

    def budget_guard(self, spent_month: int, *, allow_unpriced: bool = False) -> BudgetGuard:
        """A guard with this run's caps and spend; ``spent_month`` from ``month_spent``."""
        manifest = self.manifest()
        caps = Caps(manifest["run_cap_micro_usd"], manifest["monthly_cap_micro_usd"])
        spent_run = self.run_spent()
        return BudgetGuard(
            caps,
            spent_run=spent_run,
            spent_month=max(spent_month, spent_run),
            allow_unpriced=allow_unpriced,
        )

    def _input_payloads(self) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM inputs WHERE kind = 'decision' ORDER BY seq"
        return [json.loads(p) for (p,) in self._db.execute(query)]

    def recorded_records(self) -> dict[str, dict[str, Any]]:
        """``{decision_id: recorded result}`` for every call that was made."""
        return {
            p["decision_id"]: self.blobs.get(p["response_blob"])
            for p in self._input_payloads()
            if p["response_blob"]
        }

    def recorded_provider(self, label: str = "") -> RecordedProvider:
        """A provider that gives back this run's results, byte for byte."""
        return RecordedProvider(self.recorded_records(), label=label or f"recorded:{self.run_id}")

    def replay_gate(self) -> RecordedRefusals:
        """A gate that refuses exactly the calls this run refused for budget."""
        return RecordedRefusals(
            {
                p["decision_id"]: Refusal(p["refusal"])
                for p in self._input_payloads()
                if p["refusal"]
            }
        )
