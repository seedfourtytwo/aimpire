"""F1 acceptance: the package skeleton and the guard-rail configuration exist.

Written by the planning model before implementation (ADR-0016). Read-only.
"""

import subprocess
import sys
import tomllib
from configparser import ConfigParser
from pathlib import Path

import pytest

import aimpire
from aimpire.cli.main import main

pytestmark = pytest.mark.acceptance

SIM = Path(__file__).resolve().parents[2]
PACKAGES = ("sim", "cognition", "persistence", "contracts", "api", "cli")
BANNED_IN_SIM = ("random", "secrets", "numpy.random", "uuid", "time", "datetime")


def test_package_layout() -> None:
    """Every planned subpackage exists and imports (ADR-0003 layout)."""
    for name in PACKAGES:
        module = __import__(f"aimpire.{name}", fromlist=["_"])
        assert module.__doc__, f"aimpire.{name} needs a docstring saying what it owns"
    assert (SIM / "src" / "aimpire" / "py.typed").exists()


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """``aimpire --version`` prints the package version and exits 0."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"aimpire {aimpire.__version__}"


def test_cli_entry_points_declared() -> None:
    """Both ``aimpire`` and the short alias ``aim`` point at the same main."""
    scripts = tomllib.loads((SIM / "pyproject.toml").read_text())["project"]["scripts"]
    assert scripts == {"aimpire": "aimpire.cli.main:main", "aim": "aimpire.cli.main:main"}


def test_python_pinned_to_314() -> None:
    project = tomllib.loads((SIM / "pyproject.toml").read_text())["project"]
    assert project["requires-python"] == ">=3.14,<3.15"
    assert (SIM / ".python-version").read_text().strip() == "3.14"


def test_import_rules_configured() -> None:
    """The simulation package may not import cognition, persistence, api or cli."""
    cfg = ConfigParser()
    cfg.read(SIM / ".importlinter")
    contract = cfg["importlinter:contract:sim-is-pure"]
    assert contract["type"] == "forbidden"
    assert contract["source_modules"].split() == ["aimpire.sim"]
    assert set(contract["forbidden_modules"].split()) == {
        "aimpire.cognition",
        "aimpire.persistence",
        "aimpire.api",
        "aimpire.cli",
    }


def _ruff_codes(code: str, filename: str) -> set[str]:
    """Lint ``code`` as if it lived at ``filename`` and return the rule codes found."""
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--output-format=concise",
            "--stdin-filename",
            filename,
            "-",
        ],
        input=code,
        capture_output=True,
        text=True,
        cwd=SIM,
        check=False,
    )
    return {word for line in out.stdout.splitlines() for word in line.split() if word[:3] == "TID"}


@pytest.mark.parametrize("module", BANNED_IN_SIM)
def test_banned_apis_configured(module: str) -> None:
    """Randomness and the clock are banned inside ``aimpire.sim`` and allowed elsewhere."""
    code = f"import {module}\n\nprint({module})\n"
    assert "TID251" in _ruff_codes(code, "src/aimpire/sim/example.py")
    assert "TID251" not in _ruff_codes(code, "src/aimpire/cognition/example.py")
