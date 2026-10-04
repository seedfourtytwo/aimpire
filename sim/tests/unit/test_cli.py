"""Unit tests for the CLI shell (beyond the acceptance tests)."""

import pytest

from aimpire.cli.main import build_parser, main


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: aimpire" in capsys.readouterr().out


def test_unknown_argument_is_an_error() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--no-such-flag"])
    assert exc.value.code == 2
