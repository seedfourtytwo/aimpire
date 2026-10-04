"""The experiment file: pre-registration and design in one YAML file (ADR-0014, ADR-0018).

Why one strict file: ADR-0014 asks that the hypothesis, the metrics and the
arms are fixed before a run. The file declares them, every run manifest
stores the file's hash, and ``verify_batch`` flags a file edited afterwards.
Unknown keys are refused so a typo cannot silently drop part of the design.

Example::

    id: e0-pilot
    hypothesis: "..."                      # required, the pre-registered claim
    metrics: {primary: usable_share_ppm, secondary: [refusal_share_ppm]}
    world: stub                            # a registered preset factory
    ticks: 30                              # days per run
    council_every: 10                      # days between councils
    checkpoint_every: 10                   # days between periodic checkpoints
    seats: 2                               # civilizations per world
    seeds: [1, 2, 3]                       # world seeds, shared by every arm (paired)
    replicates: 3                          # runs per seed and rotation (at least 3)
    arms:
      - id: places
        knowledge_arm: A0                  # ADR-0018: A0 to A3, a label on every run
        renderer: places                   # places or grid (ADR-0013)
        prompt: base                       # base, or a text file beside this one
        models: [rule:hold, ../profiles/ollama-example.toml]

Prompt files are paraphrases of the neutral system prompt (ADR-0014 s. 3);
their hash goes into each run manifest. They must stay neutral (ADR-0019).
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

import yaml

from aimpire.cognition.minds import MindError, MindSpec, resolve_mind
from aimpire.cognition.profiles import ProfileError
from aimpire.cognition.render import system_prompt
from aimpire.cognition.seats import RENDERERS, Renderer
from aimpire.experiments.summary import METRIC_OUTCOMES
from aimpire.experiments.worlds import world_names

KNOWLEDGE_ARMS: Final = frozenset({"A0", "A1", "A2", "A3"})
MIN_REPLICATES: Final = 3  # ADR-0014 section 1
BASE_PROMPT: Final = "base"
_ID: Final = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
_TOP: Final = frozenset(
    {"id", "hypothesis", "metrics", "world", "ticks", "council_every", "checkpoint_every"}
    | {"seats", "seeds", "replicates", "arms"}
)
_ARM: Final = frozenset({"id", "knowledge_arm", "renderer", "prompt", "models"})
_PRIMARY: Final = frozenset({"primary"})
_SECONDARY: Final = frozenset({"secondary"})


class ExperimentError(ValueError):
    """An experiment file that is not a complete, valid pre-registration."""


def file_hash(path: Path) -> str:
    """BLAKE2b-256 of the file's bytes, hex: any edit, even a comment, changes it."""
    return hashlib.blake2b(path.read_bytes(), digest_size=32).hexdigest()


def text_hash(text: str) -> str:
    """BLAKE2b-256 of UTF-8 text, hex."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=32).hexdigest()


@dataclass(frozen=True, slots=True)
class Arm:
    """One condition: knowledge arm, renderer, system prompt, and the minds to rotate."""

    id: str
    knowledge_arm: str
    renderer: Renderer
    prompt: str
    prompt_text: str
    models: tuple[MindSpec, ...]

    @property
    def prompt_hash(self) -> str:
        """Hash of the system prompt text this arm sends."""
        return text_hash(self.prompt_text)


@dataclass(frozen=True, slots=True)
class Experiment:
    """A validated experiment file. Times are in ticks (days)."""

    id: str
    file_hash: str
    hypothesis: str
    primary_metric: str
    secondary_metrics: tuple[str, ...]
    world: str
    ticks: int
    council_every: int
    checkpoint_every: int
    seats: int
    seeds: tuple[int, ...]
    replicates: int
    arms: tuple[Arm, ...]


def _keys(
    table: object, required: frozenset[str], where: str, optional: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """``table`` as a dict holding every required key and nothing unknown."""
    if not isinstance(table, dict):
        raise ExperimentError(f"{where} must be a mapping")
    found = cast(dict[str, Any], table)
    if missing := sorted(required - set(found)):
        raise ExperimentError(f"{where}: missing {missing}")
    if unknown := sorted(set(found) - required - optional):
        raise ExperimentError(f"{where}: unknown keys {unknown}")
    return found


def _slug(value: object, what: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ExperimentError(f"{what} must be lowercase letters, digits and dashes, got {value!r}")
    return value


def _int(raw: dict[str, Any], key: str, minimum: int) -> int:
    value = raw[key]
    if type(value) is not int or value < minimum:
        raise ExperimentError(f"{key} must be an int >= {minimum}, got {value!r}")
    return value


def _choice(value: object, allowed: frozenset[str] | list[str], what: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ExperimentError(f"{what} must be one of {sorted(allowed)}, got {value!r}")
    return value


def _metric_names(raw: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    table = _keys(raw["metrics"], _PRIMARY, "metrics", optional=_SECONDARY)
    names = list(METRIC_OUTCOMES)
    primary = _choice(table["primary"], names, "metrics.primary")
    secondary = table.get("secondary", [])
    if not isinstance(secondary, list):
        raise ExperimentError("metrics.secondary must be a list")
    return primary, tuple(
        _choice(s, names, "metrics.secondary") for s in cast(list[Any], secondary)
    )


def _prompt(name: object, base_dir: Path) -> str:
    if name == BASE_PROMPT:
        return system_prompt()
    if not isinstance(name, str) or not (base_dir / name).is_file():
        raise ExperimentError(f"prompt must be {BASE_PROMPT!r} or a text file, got {name!r}")
    return (base_dir / name).read_text(encoding="utf-8")


def _arm(table: object, base_dir: Path, index: int) -> Arm:
    raw = _keys(table, _ARM, f"arms[{index}]")
    models = raw["models"]
    if not isinstance(models, list) or not models:
        raise ExperimentError(f"arms[{index}].models must be a non-empty list")
    try:
        minds = tuple(resolve_mind(str(m), base_dir) for m in cast(list[Any], models))
    except (MindError, ProfileError) as exc:
        raise ExperimentError(f"arms[{index}].models: {exc}") from None
    if len({m.label for m in minds}) != len(minds):
        raise ExperimentError(f"arms[{index}].models repeats a mind")
    return Arm(
        id=_slug(raw["id"], f"arms[{index}].id"),
        knowledge_arm=_choice(raw["knowledge_arm"], KNOWLEDGE_ARMS, "knowledge_arm"),
        renderer=cast(Renderer, _choice(raw["renderer"], RENDERERS, "renderer")),
        prompt=str(raw["prompt"]),
        prompt_text=_prompt(raw["prompt"], base_dir),
        models=minds,
    )


def _seeds(value: object) -> tuple[int, ...]:
    seeds = cast(list[Any], value) if isinstance(value, list) else []
    if (
        not seeds
        or any(type(s) is not int or s < 0 for s in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ExperimentError("seeds must be a non-empty list of distinct ints >= 0")
    return tuple(seeds)


def load_experiment(path: Path) -> Experiment:
    """Read and validate ``path``. Raises ``ExperimentError`` naming the first problem."""
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExperimentError(f"{path}: not valid YAML ({exc})") from None
    raw = _keys(loaded, _TOP, str(path))
    hypothesis = raw["hypothesis"]
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        raise ExperimentError("hypothesis must be a non-empty string")
    arms_raw = raw["arms"]
    if not isinstance(arms_raw, list) or not arms_raw:
        raise ExperimentError("arms must be a non-empty list")
    arms = tuple(_arm(a, path.parent, i) for i, a in enumerate(cast(list[Any], arms_raw)))
    if len({a.id for a in arms}) != len(arms):
        raise ExperimentError("arm ids must be unique")
    primary, secondary = _metric_names(raw)
    return Experiment(
        id=_slug(raw["id"], "id"),
        file_hash=file_hash(path),
        hypothesis=hypothesis.strip(),
        primary_metric=primary,
        secondary_metrics=secondary,
        world=_choice(raw["world"], world_names(), "world"),
        ticks=_int(raw, "ticks", 1),
        council_every=_int(raw, "council_every", 1),
        checkpoint_every=_int(raw, "checkpoint_every", 1),
        seats=_int(raw, "seats", 1),
        seeds=_seeds(raw["seeds"]),
        replicates=_int(raw, "replicates", MIN_REPLICATES),
        arms=arms,
    )
