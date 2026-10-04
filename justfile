# Aimpire task runner — CI calls ONLY these recipes, so local == CI.
# Python/client recipes (lint, typecheck, test, golden, schema-check, client-*) are added in E1 / client prototype.

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
    uvx zizmor --offline $(ls .github/workflows/*.yml ci/workflows/*.yml 2>/dev/null)

# Repo hygiene: file sizes, source line limits, forbidden artifacts (AGENTS.md §4.1)
hygiene:
    python3 tools/checks/repo_hygiene.py

# Lint + format-check repo tooling and Claude Code hooks (limits from ruff.toml)
lint-tools:
    uvx ruff check tools .claude/hooks
    uvx ruff format --check tools .claude/hooks

# Tests for repo tooling and Claude Code hooks
test-tools:
    uvx pytest -q tools/tests

# Install local git hooks (prek, pre-commit compatible)
hooks-install:
    uvx prek install

# Repo-wide gates that run on every PR regardless of paths
check-repo: hygiene lint-tools test-tools

# Everything CI checks (grows as code lands)
check: check-repo docs lint-workflows
