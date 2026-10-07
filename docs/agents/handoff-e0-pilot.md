# Handoff: E0 pilot on the creator's laptop

- **From:** planning session, 2026-10-06 (cloud). **For:** a local Claude Code session in `~/aimpire`.
- **Why local:** the pilot needs the laptop's own Ollama on `localhost:11434`. Cloud sessions and the desktop app's sandboxed shell cannot reach it.

## What changed (uncommitted on `main` in the working tree; commit it first)

| file | change |
|---|---|
| `profiles/qwen3-8b-8k.Modelfile` | new: `qwen3:8b` with `num_ctx 8192` |
| `profiles/ollama-8k.toml` | now tracked; comments fixed (the model is a local build, not a registry tag); `max_output_tokens` 4096 → 6144 |
| `experiments/e0-ollama-pilot.yaml`, `experiments/e0-ollama.yaml` | every model seat names `ollama-8k.toml` instead of `ollama-example.toml` |
| `docs/experiments/e0-preregistration.md` | section 3 table names the 8k profile and the Modelfile |
| `docs/agents/STATUS.md` | brought up to 2026-10-06 |

`just check` passed in the cloud copy (478 tests). `aimpire batch e0-ollama-pilot.yaml --verify` matches.

**Why this is allowed:** the pre-registration may change until the first live run of E0 exists. None exists: the only live runs so far are seed-1 trials of `aimpire run m0`, which are not E0.

## Evidence behind the change (seed 1, 2026-10-06, exploratory)

- `ollama-example` (`qwen3:8b`): every call was `ConnectError` after 2 ms; Ollama was not answering at that moment. No data.
- `ollama-8k` (`qwen3-8b-8k`), two 120-day games: replies arrived in 40–130 s with 1,500–4,300 output tokens; one of 24 was `TRUNCATED` at the 4,096 cap. Every council was `PARTIAL`, never `VALID`: a message to an unknown recipient and an uncited belief in nearly every reply, and after deaths, more workers allocated than were alive. The validator rejected those parts correctly.
- Behaviour: the mind moved the whole camp repeatedly (PL04, PL08, PL04, PL03, PL02, PL06), sent everyone to one place, and only cut the ration at day 110. Survivors at day 120: 1 and 3 of 30. `rule:half_full` keeps 30 on this seed.
- Run folders: `runs/try2/`, `runs/try3/`, `runs/m0-ollama-*`.

## Steps for the local session

1. Commit the changes above on a branch (`agent/e0-pilot-setup`), open a PR, merge when CI is green. Title: `chore(experiments): run E0's Ollama arm on qwen3:8b with an 8k context`.
2. Build the model: `ollama pull qwen3:8b && ollama create qwen3-8b-8k -f profiles/qwen3-8b-8k.Modelfile`.
3. `cd sim && uv run aimpire qualify ../profiles/ollama-8k.toml`. On FAIL: stop, report the qualify report, do not run the pilot.
4. Launch the pilot detached so it survives the session:
   `nohup uv run aimpire batch ../experiments/e0-ollama-pilot.yaml --out runs/e0 > runs/e0-pilot.log 2>&1 &`
   Check the first 3 model runs against the stop rule (pre-registration section 8: more than 20 % `TIMEOUT` or `PROVIDER_ERROR` means stop and fix the setup).
5. When it finishes: read `runs/e0/e0-ollama-pilot/report.md`, apply the seed-count rule (any model arm whose replicates differ by more than 200,000 ppm on either seed → `e0-ollama.yaml` goes to seeds 1001–1020, committed before its first run), write the pilot notes, update `STATUS.md`.
6. Then `e0-ollama.yaml` the same way (about 2½ days).

Keep the laptop plugged in and stop it from sleeping while a batch runs.
