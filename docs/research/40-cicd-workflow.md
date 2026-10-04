# 40 — Repository, CI/CD and agent workflow

!!! note "Review note, 2026-10-04"
    Where this note conflicts with an ADR or with `docs/plan/roadmap.md`, they win. Epic numbers E1–E15 were replaced by F1–F6 and M0–M8. Agent guard rails and model tiering are now in ADR-0016.

Author: DevOps/workflow lead agent · 2026-10-04 · Status: proposal (feeds ADR-0006)

Principles: **local-first, zero paid infra, zero LLM credentials in default CI**, determinism is a first-class CI gate, and the client choice (Godot 4 vs TypeScript web) stays isolated behind one directory and one workflow.

## 1. Monorepo layout

```
aimpire/
├── sim/                      # Python authoritative backend (uv project)
│   ├── src/aimpire/      # engine, rules, cognition, api (FastAPI)
│   ├── tests/{unit,property,golden,contract}/
│   └── pyproject.toml        # ruff, pyright, pytest, hypothesis config
├── schema/                   # SOURCE OF TRUTH for backend<->client contracts
│   ├── jsonschema/           # generated from Pydantic, committed
│   └── VERSION               # contract semver
├── client/                   # exactly ONE of: client/godot/  |  client/web/
├── fixtures/
│   ├── golden/               # seeds + recorded decision logs + expected checkpoint hashes
│   └── worlds/               # small authored worlds for tests
├── evals/                    # live-model eval configs, budgets (never run by default CI)
├── tools/                    # scripts: schema export, hash replay, bench compare
├── docs/
│   ├── adr/                  # NNNN-title.md (MADR-lite)
│   ├── architecture/         # C4-ish diagrams, data flow, tick pipeline
│   ├── domain-rules/         # versioned transformation rules, needs/labor/etc.
│   ├── experiments/          # experiment write-ups (seed, config, provenance, results)
│   └── agents/               # handoff notes, task board conventions
├── deploy/                   # Dockerfile, compose.yaml (backend + Ollama), devcontainer
├── .claude/                  # settings.json, commands/, agents/, skills/
├── .github/                  # workflows/, ISSUE_TEMPLATE/, CODEOWNERS, PR template, dependabot.yml
├── CLAUDE.md  AGENTS.md(→symlink)  justfile  .pre-commit-config.yaml
└── CHANGELOG.md  release-please-config.json  .release-please-manifest.json
```

Path filters: `sim/**`, `schema/**`, `fixtures/**` → backend jobs; `client/**`, `schema/**` → client jobs; `docs/**` → docs job. Use a single `ci.yml` with a `changes` job (dorny/paths-filter or `git diff` script) plus an always-run `ci-ok` aggregator job, so **branch protection requires only `ci-ok`** (path-filtered workflows that don't run otherwise block merges forever).

## 2. Verified action versions (2026-10-04, via `git ls-remote --tags` on each repo)

| Action / tool | Latest | Notes |
|---|---|---|
| actions/checkout | v7.0.1 (`3d3c42e5aac5ba805825da76410c181273ba90b1`) | |
| astral-sh/setup-uv | v10.2.0 (`c18668ad3cf93ea998bef934396af7bb5c839dc7`) | built-in cache; uv 0.12.23 |
| actions/setup-node | v7.0.0 (`820762786026740c76f36085b0efc47a31fe5020`) | web variant only |
| actions/cache | v6.1.0 | |
| actions/upload-artifact / download-artifact | v7.0.1 (`043fb46d…`) / v8.0.1 | |
| googleapis/release-please-action | v5.0.0 (`45996ed1f6d02564a971a2fa1b5860e934307cf7`) | |
| anthropics/claude-code-action | v1.0.241 (`400f8c3b3562dd02bfa65aba481641b97dbafe23`) | v1 line |
| chickensoft-games/setup-godot | v2.4.3 (`ac93246ea68518a384c1c280a496e5989341f2f6`) | Godot 4.7.2-stable current |
| abarichello/godot-ci | v3.2.1 | container alternative |
| github/codeql-action | v4.38.2 | |
| actions/dependency-review-action | v5.0.0 | |
| gitleaks/gitleaks-action | v3.0.0 | or run gitleaks via prek |
| docker/build-push-action, login, metadata, setup-buildx | v7.4.0, v4.6.0, v6.2.0, v4.4.1 | |
| actions/upload-pages-artifact, deploy-pages, configure-pages | v5.0.0, v5.0.1, v6.0.0 | |
| actions/attest-build-provenance | v4.2.2 | OIDC, free for public repos |
| j178/prek-action / prek | v3.0.0 / 0.5.4 | |
| zizmorcore/zizmor-action | v0.6.4 | workflow linter |
| step-security/harden-runner | v2.21.1 | optional egress audit |
| astral-sh/ty | 0.0.84 | still pre-1.0 → advisory only |

Sources: https://github.com/actions/checkout, https://github.com/astral-sh/setup-uv, https://github.com/actions/setup-node, https://github.com/actions/cache, https://github.com/actions/upload-artifact, https://github.com/googleapis/release-please-action, https://github.com/anthropics/claude-code-action, https://github.com/chickensoft-games/setup-godot, https://github.com/abarichello/godot-ci, https://github.com/j178/prek, https://github.com/zizmorcore/zizmor-action. Re-verify SHAs when bootstrapping; Dependabot then owns them.

**Supply-chain hygiene**
- Pin every third-party action by full commit SHA with `# vX.Y.Z` comment; enable the repo/org policy that *requires* SHA pinning (https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/).
- `dependabot.yml`: ecosystems `github-actions`, `uv`, `npm` (web) / none (Godot), `docker`; weekly, grouped, with `cooldown: default-days: 7` to avoid freshly-compromised releases.
- Top-level `permissions: {}` (or `contents: read`); grant per job. No `pull_request_target` except for nothing. `persist-credentials: false` on checkout.
- `zizmor` in PR CI on `.github/workflows/**`.
- OIDC only where needed: `id-token: write` for `attest-build-provenance` and Pages deploy. GHCR push uses `GITHUB_TOKEN` with `packages: write`. No long-lived cloud secrets exist.
- `uv.lock` / lockfiles committed; CI runs `uv sync --locked`.

## 3. Workflows

| Workflow | Trigger | Jobs | Runner / budget |
|---|---|---|---|
| `ci.yml` | `pull_request`, `push: main`, `merge_group` | changes → py-lint (ruff format --check, ruff check), py-types (pyright; ty advisory), py-test (pytest unit+hypothesis, `--hypothesis-profile=ci`), **determinism** (golden replay: recorded decisions → identical checkpoint hashes; plus same-seed double run equality), **contract** (regenerate JSON Schema from Pydantic → `git diff --exit-code schema/`; client validates fixtures against schema), client-build/test (variant), docs (mkdocs build --strict), workflows-lint (zizmor), ci-ok | ubuntu-latest, target < 10 min |
| `nightly.yml` | `schedule` 03:17 UTC, `workflow_dispatch` | long seeded batch (N seeds × M ticks, mock+rule providers), invariant checks, hash-matrix on Linux+Windows (cross-OS determinism), benchmarks (pytest-benchmark → JSON → compare to `gh-pages/bench` history, fail on >15% regression), artifact upload (14-day retention) | ubuntu + windows, ≤ 60 min |
| `release-please.yml` | `push: main` | release-please → on `release_created`: build sim wheel/sdist, desktop client exports (Linux x86_64, Windows x86_64), Docker image → GHCR (`ghcr.io/<owner>/aimpire-sim:{semver,sha}`), attest provenance, upload to GitHub Release | ubuntu (Godot exports Windows from Linux) |
| `pages.yml` | release published, `workflow_dispatch` | build web client demo (Godot web export or Vite build) + docs site → deploy-pages | ubuntu |
| `eval-live.yml` | **`workflow_dispatch` only** (inputs: provider, models, seeds, ticks, `max_usd`, `max_tokens`) | job uses `environment: live-eval` (required reviewer = creator; secrets live only there); runs evals with hard token/USD caps enforced in code and `timeout-minutes`; uploads report | ubuntu; capped e.g. $5/run default |
| `security.yml` | PR + weekly | CodeQL (python, javascript-typescript if web; `actions` language), dependency-review (PR, fail on high), gitleaks (or rely on GitHub push protection + secret scanning, free on public repos) | ubuntu |
| `claude.yml` | `issue_comment`/`pull_request_review_comment` containing `@claude`, label `claude-review` | claude-code-action review/triage | opt-in, see §5 |

Godot note: use single-threaded web export (Godot ≥4.3) so GitHub Pages works without COOP/COEP headers. Godot exports need export templates; setup-godot caches them.

### PR workflow skeleton (`.github/workflows/ci.yml`)

```yaml
name: ci
on:
  pull_request:
  push: { branches: [main] }
  merge_group:
permissions: {}
concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }
env: { CLIENT: godot }   # or: web  — the ONLY switch for client variant

jobs:
  changes:
    runs-on: ubuntu-latest
    permissions: { contents: read, pull-requests: read }
    outputs: { sim: ${{ steps.f.outputs.sim }}, client: ${{ steps.f.outputs.client }}, docs: ${{ steps.f.outputs.docs }} }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with: { persist-credentials: false }
      - id: f
        uses: dorny/paths-filter@<sha> # vX
        with:
          filters: |
            sim:    ['sim/**','schema/**','fixtures/**','uv.lock']
            client: ['client/**','schema/**']
            docs:   ['docs/**','mkdocs.yml']

  python:
    needs: changes
    if: needs.changes.outputs.sim == 'true'
    runs-on: ubuntu-latest
    permissions: { contents: read }
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with: { persist-credentials: false }
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
        with: { enable-cache: true }
      - run: uv sync --locked --all-extras
      - run: just lint            # ruff format --check + ruff check
      - run: just typecheck       # pyright (ty: continue-on-error)
      - run: just test            # unit + property (hypothesis ci profile)
      - run: just golden          # replay fixtures/golden -> compare checkpoint hashes
      - run: just schema-check    # export schema, git diff --exit-code schema/
        env: { AIMPIRE_PROVIDERS: mock,rule }   # hard guard: no network providers

  client:
    needs: changes
    if: needs.changes.outputs.client == 'true'
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with: { persist-credentials: false }
      - if: env.CLIENT == 'godot'
        uses: chickensoft-games/setup-godot@ac93246ea68518a384c1c280a496e5989341f2f6 # v2.4.3
        with: { version: 4.7.2, use-dotnet: false, include-templates: true }
      - if: env.CLIENT == 'web'
        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with: { node-version: 24, cache: npm, cache-dependency-path: client/web/package-lock.json }
      - run: just client-test     # GdUnit4 headless | vitest + tsc --noEmit
      - run: just client-contract # validate schema/ fixtures against client decoders
      - run: just client-build    # headless export / vite build (smoke)

  docs:
    needs: changes
    if: needs.changes.outputs.docs == 'true'
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with: { persist-credentials: false }
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
      - run: uvx --with mkdocs-material mkdocs build --strict

  ci-ok:   # the ONLY required status check
    if: always()
    needs: [changes, python, client, docs]
    runs-on: ubuntu-latest
    permissions: {}
    steps:
      - run: |
          [[ "${{ contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled') }}" == "false" ]]
```

## 4. Branch, merge and release policy

- **Trunk-based.** `main` always green and releasable. Branches `type/short-slug` (e.g. `feat/trade-negotiation`, `agent/<agent-name>/<slug>`), lifetime ≤ 2–3 days.
- **Ruleset on `main`:** PR required; required check `ci-ok` (+ `security / dependency-review`); linear history; **squash merge only**, PR title = squash commit; dismiss stale approvals; block force-push/deletion; merge queue optional (workflows already listen on `merge_group`). Solo creator: require 1 approval from CODEOWNERS on protected paths only, otherwise allow self-merge after green CI.
- **Conventional Commits** enforced on PR titles (`amannn/action-semantic-pull-request` or a commit-msg prek hook). Scopes: `sim`, `rules`, `cognition`, `schema`, `client`, `docs`, `ci`, `evals`.
- **Breaking-change triggers:** any `schema/` contract break → `feat(schema)!:`; any change that alters golden hashes → must bump `RULES_VERSION` and regenerate fixtures in the same PR with label `golden-update` and an explanation (never silently).
- **CODEOWNERS:** `/sim/src/aimpire/engine/`, `/schema/`, `/fixtures/golden/`, `/.github/`, `/docs/adr/`, `/.claude/` → creator.
- **Templates:** `.github/pull_request_template.md` (summary, linked issue/ADR, determinism impact Y/N, schema impact Y/N, DoD checklist, agent session link). Issue forms: `feature.yml`, `bug.yml` (seed + run config + replay file required), `experiment.yml` (hypothesis, config, seeds, metrics, budget), `adr.yml` (context, options, decision owner).
- **Releases:** release-please (manifest mode, single version for the product while 0.x; split per-component later if needed) maintains a release PR with CHANGELOG; merging it tags `vX.Y.Z` and fires build jobs. 0.x until first public demo. GitHub immutable releases on; artifacts get build-provenance attestations. Docker image is optional convenience; native `uv run aimpire` is the primary path.

## 5. AI-agent workflow

**CLAUDE.md (root, <~200 lines)** — product invariants (authoritative sim, typed proposals, truth/perception/belief separation, determinism rules: no `random` without the seeded RNG, no wall-clock in sim, stable iteration order, no set/dict-order dependence), commands (`just check` before any PR), layout map, "never touch `fixtures/golden` without label", "never add network calls to default tests", ADR pointer. Nested `sim/CLAUDE.md`, `client/CLAUDE.md` for local conventions. `AGENTS.md` symlink for other tools.

**`.claude/`** (https://code.claude.com/docs/en/common-workflows, https://code.claude.com/docs/en/sub-agents):
- `settings.json` — allow `just *`, `uv run *`, `git` read ops, `gh pr *`; deny `rm -rf`, `git push --force`, reading `.env*`, network to provider APIs; hooks: PostToolUse runs `ruff format` on edited `.py`; Stop hook runs `just check-fast`.
- `commands/` (or `skills/`): `/adr <title>` (new ADR from template), `/experiment` (scaffold docs/experiments entry + config), `/golden-update` (regenerate + explain hash diff), `/handoff` (write `docs/agents/handoff-<branch>.md`), `/dod` (run checklist).
- `agents/`: `sim-reviewer` (determinism and rule-validation review), `schema-guardian` (contract diff review), `test-writer` (property tests), `docs-writer`.

**Parallel agents without conflicts**
- One agent = one issue = one branch = one git worktree: `claude --worktree <slug>` (Claude Code native) or `git worktree add ../aimpire-<slug> -b agent/<slug>`. Use `.worktreeinclude` to copy local `.env`/model config.
- Claim work by assigning the issue + `in-progress` label; split work along module seams (rules vs cognition vs client) to minimise overlap.
- Hot files serialised: `schema/`, `uv.lock`, `fixtures/golden/`, `CHANGELOG.md` (release-please only). Agents needing a schema change open a small schema-first PR that merges before dependent work.
- Rebase on `main` before PR; small PRs (< ~400 lines diff excl. generated).
- Session continuity: every PR body links the handoff note; `docs/agents/STATUS.md` holds the current roadmap slice.

**claude-code-action (opt-in, paid)** — `claude.yml` triggers only on `@claude` mentions by write-access users or the `claude-review` label; uses `claude_code_oauth_token` (subscription) or `ANTHROPIC_API_KEY` stored in an environment; set `claude_args: "--max-turns 15 --model <chosen>"`, `use_sticky_comment: true`, no `allowed_bots: '*'`, never check out untrusted fork heads at workspace root, minimal `permissions` (contents/pull-requests/issues write only as needed). Setup via `/install-github-app` (needs repo admin). It never runs in `ci.yml`. Sources: https://github.com/anthropics/claude-code-action, https://github.com/anthropics/claude-code-action/blob/main/docs/security.md.

**Definition of done** (PR template checkbox list): `just check` green locally; tests added (unit + property where invariant-bearing); determinism impact declared, golden hashes unchanged or justified; schema regenerated and client updated; no new network dependency in default path; docs/domain-rules updated for rule changes; ADR added/updated for architectural decisions; CHANGELOG via conventional title; handoff note written if work continues.

**ADR process:** MADR-lite, `docs/adr/NNNN-kebab-title.md`, statuses Proposed → Accepted → Superseded-by-NNNN. Any agent may write a Proposed ADR; only the creator accepts. ADRs are immutable once accepted (supersede, don't edit).

## 6. Local dev parity

- **justfile** (preferred over Make; cross-platform incl. Windows laptop): `setup`, `lint`, `fmt`, `typecheck`, `test`, `test-prop`, `golden`, `golden-update`, `schema-export`, `schema-check`, `client-*`, `check-fast`, `check` (= exactly what `ci.yml` runs), `bench`, `serve` (FastAPI on 127.0.0.1), `demo` (mock providers), `eval-live` (refuses without explicit `--budget`). CI calls only `just` recipes → parity by construction.
- **prek** (Rust, drop-in for pre-commit config; used by CPython/FastAPI/Godot) with `.pre-commit-config.yaml`: ruff, ruff-format, check-yaml/toml, end-of-file, gitleaks, zizmor, conventional-commit msg hook, schema-export-if-models-changed. https://github.com/j178/prek
- **devcontainer** optional (Python + uv + just + Godot headless), mainly for cloud Claude Code sessions.
- **compose.yaml** optional: `sim` (built image, port bound `127.0.0.1:8000`) + `ollama` (profile `gpu` with NVIDIA device reservation for the RTX 2070S; CPU profile for the server). Never required for tests.

---

## ADR-0006: Repository, CI/CD and agent workflow

**Status:** Proposed · **Date:** 2026-10-04 · **Deciders:** creator

**Context.** Months-long project built mostly by Claude Code agents in parallel plus the creator. Determinism and backend↔client contracts are nonnegotiable; no paid infrastructure; default runs need no LLM credentials; client technology undecided.

**Decision.**
1. Single monorepo: `sim/`, `schema/`, `client/<variant>/`, `fixtures/`, `evals/`, `docs/`, `deploy/`, `.claude/`, `.github/`.
2. GitHub Actions on free hosted runners. One path-filtered `ci.yml` with aggregate `ci-ok` as the sole required check; determinism golden-replay and schema-diff are blocking gates. Nightly long-seed + cross-OS hash + benchmark trend. Live-model evals only via `workflow_dispatch` behind a `live-eval` environment with required reviewer and enforced budget caps.
3. Trunk-based, short-lived branches, squash merge, Conventional Commits, release-please semver releases producing Linux/Windows artifacts, optional GHCR image and Pages demo, with build provenance.
4. Supply chain: SHA-pinned actions, Dependabot with cooldown, least-privilege `permissions`, zizmor, CodeQL, dependency review, gitleaks/push protection; OIDC only for attestation/Pages.
5. Agents: CLAUDE.md + `.claude/` commands/agents/hooks; one issue/branch/worktree per agent; serialized hot files; DoD checklist; ADRs proposed by anyone, accepted by creator. claude-code-action is opt-in (mention/label), never part of required CI.
6. Local parity through `just` recipes invoked identically by CI; prek for hooks; devcontainer and Compose (with Ollama) optional.

**Consequences.** + Reproducible, free, agent-friendly; determinism regressions caught at PR time; client swap touches one directory and one env var. − Golden fixtures require disciplined regeneration; SHA pins add Dependabot PR noise (grouped weekly); Windows determinism may expose float/ordering issues early (desired). Revisit when client is chosen (ADR-000x) and if benchmark noise on shared runners proves too high (then move benchmarks to a self-hosted runner on the creator's server).
