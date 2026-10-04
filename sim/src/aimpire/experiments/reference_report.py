"""Run a reference file and write its page, data and charts; verify them later (backlog M0d).

``aimpire batch <reference.yaml> --out <folder>`` lands here when the file
says ``kind: reference``. Into ``<folder>`` it writes:

    <id>.md          the page (``report.reference``)
    <id>.json        every number on the page, and each run's final state hash
    <id>/<measure>.svg   one small-multiple chart per measure (``report.band_panels``)

With ``--out docs/experiments`` this is the committed reference page. The
output holds no clock and no machine path, so the same file always writes
the same bytes, whatever ``--jobs`` is. A reference spends nothing: it runs
rule minds only.

``verify_reference`` compares the file's hash with the one in ``<id>.json``,
so an edit of the reference file after its bands were made is visible.
"""

import json
from pathlib import Path
from typing import Any, Final

from aimpire.experiments.preflight import Echo
from aimpire.experiments.reference import load_reference, reference_data, run_reference
from aimpire.report.band_panels import Panel, band_panels_svg
from aimpire.report.reference import reference_markdown

_DIVISORS: Final = {"stores_mu": 1000, "near_camp_mu": 1000}


def _charts(data: dict[str, Any], out_root: Path) -> list[str]:
    """Write one SVG per measure; return their paths relative to ``out_root``."""
    ref = data["reference"]
    ticks = data["checkpoints"]
    year = ref["ticks_per_year"]
    labels = ("year 0", f"year {ticks[-1] // year}") if year else None
    folder = out_root / ref["id"]
    folder.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for measure in data["measures"]:
        panels = [
            Panel(
                m["mind"].removeprefix("rule:"),
                m["bands"][measure]["q10"],
                m["bands"][measure]["median"],
                m["bands"][measure]["q90"],
            )
            for m in data["minds"]
        ]
        svg = band_panels_svg(ticks, panels, divisor=_DIVISORS.get(measure, 1), x_labels=labels)
        name = f"{ref['id']}/{measure}.svg"
        (out_root / name).write_text(svg, encoding="utf-8")
        names.append(name)
    return names


def write_reference(data: dict[str, Any], out_root: Path) -> Path:
    """Write the page, the JSON and the charts under ``out_root``; return the page path."""
    out_root.mkdir(parents=True, exist_ok=True)
    data = {**data, "charts": _charts(data, out_root)}
    ref_id = data["reference"]["id"]
    page = out_root / f"{ref_id}.md"
    page.write_text(reference_markdown(data), encoding="utf-8")
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    (out_root / f"{ref_id}.json").write_text(text, encoding="utf-8")
    return page


def run_reference_file(path: Path, *, out_root: Path, jobs: int = 1, echo: Echo = print) -> Path:
    """Load, run and write the reference at ``path``. Free: rule minds only."""
    spec = load_reference(path)
    runs = len(spec.minds) * len(spec.seeds)
    echo(f"reference {spec.id}: {runs} runs of rule minds, cost $0 (nothing is called)")
    page = write_reference(reference_data(spec, run_reference(spec, jobs=jobs)), out_root)
    echo(f"report {page}")
    return page


def verify_reference(path: Path, *, out_root: Path) -> bool:
    """Whether ``<id>.json`` under ``out_root`` was made from ``path`` as it is now."""
    spec = load_reference(path)
    data_path = out_root / f"{spec.id}.json"
    if not data_path.is_file():
        raise FileNotFoundError(data_path)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return data["reference"]["file_hash"] == spec.file_hash
