-- 0001: the run store (ADR-0004). One SQLite database per run at runs/<run_id>/run.db.
-- Amounts are integer micro-dollars. Seeds are decimal TEXT: a u64 seed does not fit
-- SQLite's signed 64-bit INTEGER. STRICT tables refuse values of the wrong type.

CREATE TABLE manifest (
    run_id                TEXT PRIMARY KEY,
    schema_version        INTEGER NOT NULL,
    created_month         TEXT NOT NULL,
    seed                  TEXT NOT NULL,
    rules_version         TEXT NOT NULL,
    rules_hash            TEXT NOT NULL,
    contract              TEXT NOT NULL,
    state_format          TEXT NOT NULL,
    draw_version          TEXT NOT NULL,
    replay_of_run_id      TEXT,
    parent_run_id         TEXT,
    branch_tick           INTEGER,
    branch_checkpoint_id  INTEGER,
    run_cap_micro_usd     INTEGER NOT NULL CHECK (run_cap_micro_usd >= 0),
    monthly_cap_micro_usd INTEGER NOT NULL CHECK (monthly_cap_micro_usd >= 0),
    python_version        TEXT NOT NULL,
    numpy_version         TEXT NOT NULL,
    sqlite_version        TEXT NOT NULL,
    code_version          TEXT NOT NULL,
    config_json           TEXT NOT NULL
) STRICT;

-- The replay source of truth: one row per decision, in the order it was applied.
-- payload_json: {decision_id, civ_id, council, response_blob, refusal}.
CREATE TABLE inputs (
    seq          INTEGER PRIMARY KEY,
    tick         INTEGER NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('decision')),
    ref          TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (kind, ref)
) STRICT;

-- Audit and metering: what was asked, who answered, the outcome, and the spend ledger.
CREATE TABLE decisions (
    decision_id        TEXT PRIMARY KEY,
    seq                INTEGER NOT NULL UNIQUE REFERENCES inputs (seq),
    tick               INTEGER NOT NULL,
    council            INTEGER NOT NULL,
    civ_id             TEXT NOT NULL,
    provider           TEXT NOT NULL,
    model              TEXT NOT NULL,
    model_digest       TEXT NOT NULL,
    model_reported     TEXT NOT NULL,
    status             TEXT NOT NULL,
    outcome            TEXT NOT NULL,
    refusal            TEXT NOT NULL,
    record_json        TEXT NOT NULL,
    request_blob       TEXT NOT NULL,
    response_blob      TEXT NOT NULL,
    input_tokens       INTEGER NOT NULL,
    output_tokens      INTEGER NOT NULL,
    reasoning_tokens   INTEGER NOT NULL,
    latency_ms         INTEGER NOT NULL,
    attempts           INTEGER NOT NULL,
    reserved_micro_usd INTEGER NOT NULL CHECK (reserved_micro_usd >= 0),
    charged_micro_usd  INTEGER NOT NULL CHECK (charged_micro_usd >= 0),
    month              TEXT NOT NULL
) STRICT;

CREATE INDEX decisions_by_month ON decisions (month);

CREATE TABLE checkpoints (
    checkpoint_id         INTEGER PRIMARY KEY,
    tick                  INTEGER NOT NULL,
    label                 TEXT NOT NULL,
    state_hash            TEXT NOT NULL,
    subsystem_hashes_json TEXT NOT NULL,
    state_blob            TEXT NOT NULL,
    UNIQUE (tick, label)
) STRICT;
