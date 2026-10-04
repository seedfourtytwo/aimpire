# Aimpire task runner — CI calls ONLY these recipes, so local == CI.

set shell := ["bash", "-euo", "pipefail", "-c"]

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
check-sim: lint typecheck test schema-check

# --- Static replay player (client/replay/) ----------------------------------

# Regenerate the fixture replay the player opens by default
fixture-replay: sync
    cd sim && uv run python scripts/make_fixture_replay.py

# Client checks: fixture valid and current; player.js syntax and headless smoke test (Node)
check-client: sync
    cd sim && uv run python scripts/make_fixture_replay.py --check
    @if command -v node >/dev/null 2>&1; then \
        node --check client/replay/player.js && \
        node client/replay/smoke-test.cjs "$(cd sim && uv run python scripts/make_fixture_replay.py --frame-sha256)"; \
    else \
        echo "node not found: skipped the player.js syntax check and smoke test (fixture still validated)"; \
    fi
