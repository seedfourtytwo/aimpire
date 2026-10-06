"""Tests for the repository hygiene gate (CLAUDE.md "Small files" size and file rules)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import repo_hygiene as rh


def _write(root: Path, rel: str, content: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _rules(violations: list[rh.Violation]) -> set[str]:
    return {v.rule for v in violations}


def test_small_source_file_has_no_violations(tmp_path: Path) -> None:
    _write(tmp_path, "sim/a.py", "x = 1\n" * 10)
    assert rh.check_paths(tmp_path, ["sim/a.py"]) == []


def test_source_file_over_hard_line_limit_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "sim/big.py", "x = 1\n" * (rh.SOURCE_LINE_HARD_LIMIT + 1))
    violations = rh.check_paths(tmp_path, ["sim/big.py"])
    assert _rules(violations) == {"source-too-long"}
    assert violations[0].is_error


def test_source_file_over_target_is_only_a_warning(tmp_path: Path) -> None:
    _write(tmp_path, "client/web/src/a.ts", "let a = 1;\n" * (rh.SOURCE_LINE_TARGET + 1))
    violations = rh.check_paths(tmp_path, ["client/web/src/a.ts"])
    assert _rules(violations) == {"source-over-target"}
    assert not violations[0].is_error


def test_markdown_is_not_line_limited(tmp_path: Path) -> None:
    _write(tmp_path, "docs/long.md", "line\n" * 2000)
    assert rh.check_paths(tmp_path, ["docs/long.md"]) == []


def test_generated_contract_code_is_exempt_from_line_limits(tmp_path: Path) -> None:
    _write(tmp_path, "client/web/src/contract/types.ts", "x;\n" * 2000)
    assert rh.check_paths(tmp_path, ["client/web/src/contract/types.ts"]) == []


def test_large_binary_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "client/web/public/big.png", b"\0" * (rh.MAX_FILE_BYTES + 1))
    assert _rules(rh.check_paths(tmp_path, ["client/web/public/big.png"])) == {"file-too-large"}


def test_lockfiles_are_allowed_to_be_large(tmp_path: Path) -> None:
    _write(tmp_path, "sim/uv.lock", "a\n" * (rh.MAX_FILE_BYTES // 2 + 10))
    assert rh.check_paths(tmp_path, ["sim/uv.lock"]) == []


def test_forbidden_artifacts_are_errors(tmp_path: Path) -> None:
    for rel in (
        "runs/r1.db",
        "runs/r1/blobs/ab.json.zst",
        "model.gguf",
        ".env",
        "sim/.env.local",
        "weights.safetensors",
        "debug.log",
        "exports/run1.csv",
        "sim/runs/r1/replay.json",
        "sim/runs/r1/notebook.md",
    ):
        _write(tmp_path, rel, "x")
        assert _rules(rh.check_paths(tmp_path, [rel])) == {"forbidden-file"}, rel


@pytest.mark.parametrize(
    "rel",
    [
        "sim/src/aimpire/api/runs/router.py",
        "client/web/src/views/runs/RunList.tsx",
        "docs/saves/x.md",
    ],
)
def test_source_folders_named_like_run_data_are_allowed(tmp_path: Path, rel: str) -> None:
    _write(tmp_path, rel, "x = 1\n")
    assert rh.check_paths(tmp_path, [rel]) == []


@pytest.mark.parametrize(
    "rel",
    ["fixtures/golden/key.pem", "fixtures/golden/r/.env", "fixtures/golden/m.gguf"],
)
def test_golden_exemption_covers_run_data_only(tmp_path: Path, rel: str) -> None:
    _write(tmp_path, rel, "x")
    assert _rules(rh.check_paths(tmp_path, [rel])) == {"forbidden-file"}


@pytest.mark.parametrize(
    ("rel", "ignored"),
    [
        ("fixtures/golden/r/run.db", False),
        ("fixtures/golden/r/blobs/a.json.zst", False),
        ("fixtures/golden/key.pem", True),
        ("runs/r1/run.db", True),
        ("sim/runs/r1/replay.json", True),
        ("sim/runs/r1/notebook.md", True),
        ("sim/src/aimpire/api/runs/router.py", False),
    ],
)
def test_gitignore_matches_hygiene_policy(rel: str, ignored: bool) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(["git", "check-ignore", "-q", "--no-index", rel], cwd=repo, check=False)
    assert (result.returncode == 0) == ignored, rel


def test_golden_fixtures_may_hold_run_artifacts(tmp_path: Path) -> None:
    for rel in (
        "fixtures/golden/shared_river/run.db",
        "fixtures/golden/shared_river/blobs/a.json.zst",
    ):
        _write(tmp_path, rel, "x")
        assert rh.check_paths(tmp_path, [rel]) == [], rel


def test_typescript_module_variants_are_line_limited(tmp_path: Path) -> None:
    _write(tmp_path, "client/web/src/a.mts", "x;\n" * (rh.SOURCE_LINE_HARD_LIMIT + 1))
    assert _rules(rh.check_paths(tmp_path, ["client/web/src/a.mts"])) == {"source-too-long"}


def test_candidate_files_handles_non_ascii_names(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _write(tmp_path, "données/é.db", "x")
    files = rh.candidate_files(tmp_path)
    assert "données/é.db" in files
    assert _rules(rh.check_paths(tmp_path, files)) == {"forbidden-file"}


def test_env_example_is_allowed(tmp_path: Path) -> None:
    _write(tmp_path, ".env.example", "ANTHROPIC_API_KEY=\n")
    assert rh.check_paths(tmp_path, [".env.example"]) == []


def test_missing_paths_are_ignored(tmp_path: Path) -> None:
    # Deleted-but-listed files must not crash the gate.
    assert rh.check_paths(tmp_path, ["gone.py"]) == []


def test_main_returns_nonzero_only_on_errors(tmp_path: Path) -> None:
    _write(tmp_path, "ok.py", "x = 1\n")
    assert rh.main(["--root", str(tmp_path), "ok.py"]) == 0
    _write(tmp_path, "bad.py", "x = 1\n" * (rh.SOURCE_LINE_HARD_LIMIT + 1))
    assert rh.main(["--root", str(tmp_path), "bad.py"]) == 1


# --- ratchet for grandfathered files ------------------------------------------------


def _baseline(tmp_path: Path, text: str) -> Path:
    return _write(tmp_path, "tools/checks/hygiene-baseline.txt", text)


def test_baselined_file_may_exceed_hard_limit_up_to_its_recorded_size(tmp_path: Path) -> None:
    _write(tmp_path, "sim/tests/acceptance/test_big.py", "x = 1\n" * 575)
    _baseline(
        tmp_path, "# path  max_lines  reason\nsim/tests/acceptance/test_big.py 575 split in G2\n"
    )
    violations = rh.check_paths(tmp_path, ["sim/tests/acceptance/test_big.py"])
    assert _rules(violations) == {"source-over-target"}
    assert not any(v.is_error for v in violations)


def test_baselined_file_may_not_grow(tmp_path: Path) -> None:
    _write(tmp_path, "sim/tests/acceptance/test_big.py", "x = 1\n" * 576)
    _baseline(tmp_path, "sim/tests/acceptance/test_big.py 575 split in G2\n")
    violations = rh.check_paths(tmp_path, ["sim/tests/acceptance/test_big.py"])
    assert _rules(violations) == {"baseline-grew"}


def test_unlisted_file_still_fails_the_hard_limit(tmp_path: Path) -> None:
    _write(tmp_path, "sim/src/new.py", "x = 1\n" * (rh.SOURCE_LINE_HARD_LIMIT + 1))
    _baseline(tmp_path, "sim/tests/acceptance/test_big.py 575 split in G2\n")
    assert _rules(rh.check_paths(tmp_path, ["sim/src/new.py"])) == {"source-too-long"}


def test_baseline_entry_without_reason_is_rejected(tmp_path: Path) -> None:
    _baseline(tmp_path, "sim/tests/acceptance/test_big.py 575\n")
    with pytest.raises(ValueError, match="reason"):
        rh.load_baseline(tmp_path)


def test_repository_baseline_entries_are_still_needed() -> None:
    # Stale entries hide regressions: once a file is split, its entry must go.
    repo = Path(__file__).resolve().parents[2]
    for rel, max_lines in rh.load_baseline(repo).items():
        path = repo / rel
        assert path.is_file(), f"baseline lists missing file {rel}"
        lines = sum(1 for _ in path.open("rb"))
        assert lines > rh.SOURCE_LINE_HARD_LIMIT, f"{rel} is back under the limit; remove its entry"
        assert lines == max_lines, (
            f"{rel}: lower its baseline to {lines} (the ratchet only tightens)"
        )
