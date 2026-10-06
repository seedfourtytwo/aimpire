# Aimpire task runner — CI calls ONLY these recipes, so local == CI.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Pinned versions for repo-wide tools (bump deliberately, in their own PR).
# `ruff` is mirrored in .claude/hooks/post_edit_check.py and .pre-commit-config.yaml.
ruff := "ruff@0.16.10"
pytest := "pytest==9.1.1"
prek := "prek@0.5.4"

default:
    @just --list

# Build the documentation site (strict: warnings fail)
docs:
    uvx --from "mkdocs<2" --with "mkdocs-material<10" mkdocs build --strict

# Serve docs locally on 127.0.0.1:8001
docs-serve:
    uvx --from "mkdocs<2" --with "mkdocs-material<10" mkdocs serve -a 127.0.0.1:8001

# Lint GitHub workflows for security issues
lint-workflows:
    uvx zizmor --offline .github/workflows

# --- Repo-wide gates (tools/, .claude/hooks/; ADR-0022) ---------------------

# Repo hygiene: file sizes, source line limits (with ratchet baseline), forbidden artifacts
hygiene:
    python3 tools/checks/repo_hygiene.py

# Lint + format-check repo tooling and Claude Code hooks (config: root ruff.toml)
lint-tools:
    uvx {{ruff}} check tools .claude/hooks
    uvx {{ruff}} format --check tools .claude/hooks

# Tests for repo tooling and Claude Code hooks
test-tools:
    uvx --from {{pytest}} pytest -q tools/tests

# Install local git hooks (prek, pre-commit compatible)
hooks-install:
    uvx {{prek}} install

# Repo-wide gates. They also run inside check-sim, so CI's python job enforces them
# until a dedicated `repo` job is added to ci.yml (backlog G1e, creator only).
check-repo: hygiene lint-tools test-tools

# Everything CI checks (grows as code lands)
check: docs lint-workflows check-sim check-client

# --- Python simulation (sim/) ---------------------------------------------

# Install the locked environment
sync:
    cd sim && uv sync --locked

# Format check and lint (ruff; config in sim/ruff.toml)
lint: sync
    cd sim && uv run ruff format --check . && uv run ruff check .

# Apply formatting and safe lint fixes
fmt: sync
    cd sim && uv run ruff format . && uv run ruff check --fix .

# Type check (pyright: strict on aimpire.sim) and architecture rules (import-linter)
typecheck: sync
    cd sim && uv run pyright && uv run lint-imports

# Full test suite
test: sync
    cd sim && uv run pytest

# Quick, quiet tests: stop at the first failure
test-fast: sync
    cd sim && uv run pytest -q -x --no-header -p no:cacheprovider

# Regenerate the contract JSON schemas into schema/ (generated files: never hand-edit)
schema-export: sync
    cd sim && uv run python -m aimpire.contracts.export ../schema

# Fail if schema/ differs from what the contracts generate (regenerates to a temp dir and diffs)
schema-check: sync
    cd sim && uv run python -m aimpire.contracts.export --check ../schema

# Python sim checks: what the CI python job runs (golden checks join later)
check-sim: check-repo lint typecheck test schema-check

# --- Static replay player (client/replay/) ----------------------------------

# Regenerate the player's fixture replays (fixtures/m0.json and fixtures/wander.json)
fixture-replay: sync
    cd sim && uv run python scripts/make_fixture_replay.py

# Client checks: fixtures valid and current; player syntax and headless smoke test (Node)
check-client: sync
    cd sim && uv run python scripts/make_fixture_replay.py --check
    @if command -v node >/dev/null 2>&1; then \
        node --check client/replay/player.js && \
        node --check client/replay/panels.js && \
        node --check client/replay/map.js && \
        node client/replay/smoke-test.cjs "$(cd sim && uv run python scripts/make_fixture_replay.py --frame-sha256)"; \
    else \
        echo "node not found: skipped the player.js syntax check and smoke test (fixture still validated)"; \
    fi
