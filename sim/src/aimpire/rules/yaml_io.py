"""Read one YAML rules file into a plain mapping (the loader's only file reading)."""

from pathlib import Path

import yaml

from aimpire.rules.errors import RulesError


def read_mapping(path: Path) -> dict[str, object]:
    """Parse ``path`` with ``yaml.safe_load``; the top level must be a mapping."""
    try:
        data: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RulesError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RulesError(f"{path} must hold a mapping")
    return {str(k): v for k, v in data.items()}  # pyright: ignore[reportUnknownVariableType]
