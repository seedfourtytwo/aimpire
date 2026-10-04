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
    uvx zizmor --offline .github/workflows

# Everything CI checks (grows as code lands)
check: docs lint-workflows

# Python sim checks: lint, typecheck, test, golden, schema (filled in by F1)
check-sim:
    @if [ -d sim ]; then echo "sim/ exists but check-sim is not implemented yet (F1)"; exit 1; else echo "no sim/ yet: nothing to check"; fi

# Web client checks (filled in by the client work)
check-client:
    @if [ -d client ]; then echo "client/ exists but check-client is not implemented yet"; exit 1; else echo "no client/ yet: nothing to check"; fi
