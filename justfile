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

# Everything CI checks (grows as code lands)
check: docs lint-workflows
