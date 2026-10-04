# Aimpire task runner — CI calls ONLY these recipes, so local == CI.
# Client recipes (client-*) arrive with the replay player and console.

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
check: docs lint-workflows check-sim

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

# Python sim checks: what the CI python job runs (golden and schema checks join later)
check-sim: lint typecheck test

# Web client checks (filled in by the client work)
check-client:
    @if [ -d client ]; then echo "client/ exists but check-client is not implemented yet"; exit 1; else echo "no client/ yet: nothing to check"; fi
