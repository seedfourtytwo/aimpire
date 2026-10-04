"""LAB0 acceptance: the knob registry and ``--set`` overrides (ADR-0020).

Written before the code, in the planning role (ADR-0016). Read-only for implementers.

Every tunable is declared once. Overrides are checked against the registry,
canonicalised into a variant with a stable id, and routed: world, rules and
tribe overrides change the rules hash; mind and god overrides only enter the
run manifest. No knob may name an outcome (ADR-0019).
"""

import ast
import json
import re
from pathlib import Path

import pytest

from aimpire.contracts.export import render_exports
from aimpire.lab.knobs import KNOBS, Layer, get_knob
from aimpire.lab.overrides import KnobError, parse_sets
from aimpire.lab.variant import resolve_variant
from aimpire.rules import load_world, rules_hash

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
SIM_PACKAGE = REPO / "sim" / "src" / "aimpire" / "sim"
KNOB_SCHEMA = REPO / "schema" / "lab-knobs.schema.json"

HASHED_LAYERS = {Layer.WORLD, Layer.RULES, Layer.TRIBE}

# ADR-0019: outcomes are not inputs. A knob may not name a personality or
# temperament, an institution or regime, a role or a belief. Versioned here.
OUTCOME_WORDS = frozenset(
    [
        "personality",
        "personalities",
        "temperament",
        "temperaments",
        "character",
        "mood",
        "moods",
        "aggressive",
        "aggression",
        "peaceful",
        "warlike",
        "hostile",
        "friendly",
        "cooperative",
        "selfish",
        "altruistic",
        "greedy",
        "brave",
        "timid",
        "loyal",
        "obedient",
        "institution",
        "institutions",
        "regime",
        "regimes",
        "government",
        "chiefdom",
        "chief",
        "chiefs",
        "king",
        "kings",
        "queen",
        "ruler",
        "rulers",
        "leader",
        "leaders",
        "monarchy",
        "democracy",
        "tyranny",
        "polity",
        "caste",
        "tax",
        "taxes",
        "tribute",
        "law",
        "laws",
        "role",
        "roles",
        "priest",
        "priests",
        "priesthood",
        "shaman",
        "elder",
        "elders",
        "warrior",
        "warriors",
        "belief",
        "beliefs",
        "religion",
        "religious",
        "faith",
        "doctrine",
        "worship",
        "deity",
        "sacred",
        "taboo",
        "myth",
    ]
)


def _words(text: str) -> set[str]:
    """Lower-case words; ``mind.knowledge_arm`` gives mind, knowledge and arm."""
    return set(re.findall(r"[a-z]+", text.lower()))


def test_registry_is_complete_and_consistent() -> None:
    """Each knob: a path in its layer, a unit, a description, a default inside both ranges."""
    paths = [knob.path for knob in KNOBS]
    assert len(paths) == len(set(paths))
    assert {"world.gravity", "world.sunlight", "world.rain", "world.tilt"} <= set(paths)
    assert any(knob.layer is Layer.MIND for knob in KNOBS)
    for knob in KNOBS:
        assert knob.path.split(".", 1)[0] == knob.layer.value
        assert knob.unit and knob.description
        assert knob.in_rules_hash is (knob.layer in HASHED_LAYERS)
        assert get_knob(knob.path) is knob
        knob.check(knob.default)  # the default is always allowed
        assert not knob.beyond_validated(knob.default)


def test_world_knob_defaults_match_world_yaml() -> None:
    world = load_world(RULES_V1)
    for name in ("gravity", "sunlight", "rain", "tilt"):
        assert get_knob(f"world.{name}").default == getattr(world, name)


def test_unknown_knob_refused() -> None:
    with pytest.raises(KnobError, match=r"unknown knob 'world\.gravityy'"):
        parse_sets(["world.gravityy=950000"])
    with pytest.raises(KnobError, match="path=value"):
        parse_sets(["world.gravity"])
    with pytest.raises(KnobError, match="more than once"):
        parse_sets(["world.gravity=950000", "world.gravity=900000"])


@pytest.mark.parametrize(
    ("setting", "fragment"),
    [
        ("world.gravity=0", "allowed range"),
        ("world.gravity=99999999", "allowed range"),
        ("world.tilt=-5", "allowed range"),
        ("world.gravity=0.95", "integer"),
        ("world.gravity=lots", "integer"),
    ],
)
def test_out_of_allowed_range_refused(setting: str, fragment: str) -> None:
    with pytest.raises(KnobError, match=fragment):
        parse_sets([setting])


def test_enum_knob_refuses_unknown_choice() -> None:
    enum_knob = next(knob for knob in KNOBS if knob.choices)
    with pytest.raises(KnobError, match="one of"):
        parse_sets([f"{enum_knob.path}=not-a-choice"])


def test_variant_id_is_canonical() -> None:
    """The id is a hash of the canonical overrides: order and spelling do not matter."""
    a = parse_sets(["world.gravity=950_000", "world.rain=800000"])
    b = parse_sets(["world.rain=800_000", "world.gravity=950000"])
    assert a.variant_id == b.variant_id
    assert a.overrides == b.overrides == (("world.gravity", 950_000), ("world.rain", 800_000))
    assert parse_sets([]).variant_id != a.variant_id


def test_world_override_changes_rules_hash() -> None:
    baseline = resolve_variant(RULES_V1, [])
    variant = resolve_variant(RULES_V1, ["world.gravity=950000"])
    assert baseline.rules_hash == rules_hash(RULES_V1)
    assert variant.rules_hash != baseline.rules_hash
    assert variant.world.gravity == 950_000
    assert abs(variant.derived.walk_speed - 974_679) <= 1
    assert baseline.derived.walk_speed == 1_000_000
    assert variant.manifest_config()["variant"]["overrides"] == {"world.gravity": 950_000}


def test_mind_override_does_not() -> None:
    """Mind overrides go into the manifest only: same rules hash, same physics, new variant id."""
    knob = next(knob for knob in KNOBS if knob.layer is Layer.MIND)
    value = next(choice for choice in knob.choices if choice != knob.default)
    baseline = resolve_variant(RULES_V1, [])
    variant = resolve_variant(RULES_V1, [f"{knob.path}={value}"])
    assert variant.rules_hash == baseline.rules_hash
    assert variant.derived == baseline.derived
    assert variant.variant.variant_id != baseline.variant.variant_id
    assert variant.manifest_config()["variant"]["overrides"] == {knob.path: value}


def test_beyond_validated_range_tags_run() -> None:
    """Allowed but unvalidated: the run is tagged beyond-model, and says which knob."""
    inside = resolve_variant(RULES_V1, ["world.gravity=900000"])
    assert "beyond-model" not in inside.tags
    outside = resolve_variant(RULES_V1, ["world.gravity=300000"])
    assert outside.variant.beyond_model == ("world.gravity",)
    assert "beyond-model" in outside.tags
    config = outside.manifest_config()
    assert "beyond-model" in config["tags"]
    assert config["variant"]["beyond_model"] == ["world.gravity"]
    json.dumps(config)  # the manifest stores it as canonical JSON


def test_no_outcome_knobs() -> None:
    """ADR-0019: no knob path or description names a personality, institution, role or belief."""
    hits = {
        knob.path: sorted(_words(f"{knob.path} {knob.description} {knob.unit}") & OUTCOME_WORDS)
        for knob in KNOBS
    }
    assert not {path: words for path, words in hits.items() if words}


def test_registry_exported_to_schema() -> None:
    """schema/lab-knobs.schema.json is generated by the export command and is current."""
    generated = render_exports()
    assert "lab-knobs.schema.json" in generated
    assert KNOB_SCHEMA.read_text(encoding="utf-8") == generated["lab-knobs.schema.json"]
    schema = json.loads(generated["lab-knobs.schema.json"])
    assert set(schema["properties"]) == {knob.path for knob in KNOBS}
    assert schema["additionalProperties"] is False


def test_sim_does_not_import_lab() -> None:
    """aimpire.lab sits above the simulation; sim/ never imports it."""
    found: list[str] = []
    for path in sorted(SIM_PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            found += [f"{path.name}: {n}" for n in names if n.startswith("aimpire.lab")]
    assert not found
