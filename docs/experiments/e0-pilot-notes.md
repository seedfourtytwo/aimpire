# E0 Ollama pilot: notes

Exploratory (pre-registration section 10), never pooled with the confirmatory runs. Run 2026-10-07 on the creator's laptop: `e0-ollama-pilot.yaml`, seeds 901 and 902, 3 replicates, `qwen3:8b` with an 8,192-token context and thinking off (`profiles/ollama-8k.toml`). About 4 hours in all (13:33 to about 17:20). Run folder: `sim/runs/e0` (not in the repo); report: `sim/runs/e0/e0-ollama-pilot/report.md`.

## Setup

- Qualify failed (order validity 26 %, mark 80 %); the pilot was run anyway as an exploratory exception (pre-registration section 3).
- Stop rule (section 8): no `TIMEOUT` or `PROVIDER_ERROR` in the first 3 model runs or after; failure share was 0 except one run at 41,666 ppm.

## Results

- **Survival:** median 0 of 30 in all four model arms (10th to 90th percentile: 0 to 33,333 ppm). Rule baselines: `random` 33,333, `greedy` 100,000, `half_full` and `msy` 1,000,000.
- **Arms do not differ:** every paired comparison between places/grid and hidden/disclosed has the same survival on both seeds. Nothing here supports or rules out H-arms; the pilot is not designed to.
- **Valid replies (of 144 councils per arm):** places-hidden 44, places-disclosed 21, grid-hidden 46, grid-disclosed 57. The rest were `PARTIAL`.
- **Behaviour:** in the one run inspected (places-hidden, seed 901, replicate 0) the ration stayed at 1000 permille for all 24 councils. At the end the people near the camp held over 2 million milli-units of food while the camp's stores were 0 and all 30 died.

## Seed rule (section 8)

Replicates of any model arm differ by at most 33,333 ppm in survival (limit 200,000), so `e0-ollama.yaml` stays at seeds 1001 to 1010.

## Open

- A model that cannot keep 30 people alive in any arm leaves little for H-arms to separate. Before the 2½-day confirmatory run, decide whether `qwen3:8b` is the right open-weight model for it.
