# Play M0: the petri dish

This page is for playing with Aimpire as it stands at milestone M0: one group of 30 people on a
flat map with one wild food that grows back. A "mind" decides every 10 days who gathers food
where. You can let a fixed rule decide, a model on your own laptop, or a paid model.

Every command below was run as written, except the ones marked **needs Ollama** or
**needs a key**, which call a model.

## 1. Set up once

You need `git` and [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs
the right Python by itself).

```bash
git clone https://github.com/seedfourtytwo/aimpire.git
cd aimpire/sim
uv sync
```

Every command from here on is typed **in the `sim` folder**. To see what exists:

```bash
uv run aimpire --help
uv run aimpire run --help
```

## 2. Play a game with a rule

A rule mind is free and instant. There are four, the same four that every model is scored
against:

| rule | what it does |
|---|---|
| `rule:random` | sends people to random places |
| `rule:greedy` | sends everyone to the place with the most food |
| `rule:half_full` | gathers only what grows back, keeping each place about half full |
| `rule:msy` | the textbook optimum for the regrowth rule |

```bash
uv run aimpire run m0 --mind rule:half_full --seed 1
uv run aimpire run m0 --mind rule:greedy --seed 1
uv run aimpire run m0 --mind rule:random --seed 1
uv run aimpire run m0 --mind rule:msy --seed 1
```

Each plays five years (600 days) and prints one line a year. With seed 1, `half_full` ends with
all 30 people alive; `greedy` with 4:

```text
  tick  year people deaths  stores near camp
     0     0     30      0     900      2383
   120     1      6     24       0        48
   ...
   600     5      4     26       0        48
```

- **people / deaths:** nobody is born in M0, so deaths only go up.
- **stores:** food the group has gathered and not yet eaten (one unit feeds one person a day;
  stores spoil a little every day).
- **near camp:** wild food still growing around the camp. When it falls to almost nothing, the
  group has eaten its own future.

Change `--seed` for a different world, `--years 2` for a shorter game. The same command always
gives exactly the same game: the last lines print a "final hash" that you can compare.

## 3. What a game leaves behind

Each game writes a folder in `sim/runs/`, named after its settings, for example
`runs/m0-rule-greedy-s1-t600-places-c10-vf4788ac6/`:

| file | what it is |
|---|---|
| `notebook.md` | the lab notebook: settings, a table of every measure, small charts, where the food went, how each council's decision ended, and the command that repeats the game |
| `chart-*.svg` | the notebook's charts (open them in a browser) |
| `metrics.csv` | every measure on every day, for a spreadsheet |
| `replay.json` | the game as frames, for the replay player |
| `run.db` | the complete record (every decision and checkpoint), for audits |

Open `notebook.md` in any Markdown viewer (VS Code, GitHub, Obsidian). The **Ledger** table
shows food grown, harvested, eaten and spoiled; the **Outcomes** table shows how each council's
decision ended (`VALID` is good; refusals and errors are counted, never hidden).

## 4. Watch the replay

The replay player is a web page. Browsers only let it load a file through a small local web
server, so start one **from the repository root** (one folder up from `sim`):

```bash
cd ..
python3 -m http.server 8000
```

Then open this address in your browser, with your run's folder name in it:

```text
http://127.0.0.1:8000/client/replay/?src=/sim/runs/m0-rule-greedy-s1-t600-places-c10-vf4788ac6/replay.json
```

The background colour shows how much wild food each tile holds, and the single dot is the
camp. Use Play, the arrows or the slider; the line under the map gives the day, year and season. Press Ctrl+C in the terminal to stop the server, and `cd sim` to go back. The player
also has a file picker if you prefer to choose `replay.json` by hand.

## 5. The Lab: change the world

`--set` changes a world constant for one game. Values are in parts per million of Earth
(1,000,000 is Earth):

```bash
uv run aimpire run m0 --mind rule:half_full --seed 1 --set world.gravity=1500000
uv run aimpire run m0 --mind rule:half_full --seed 1 --set world.sunlight=500000
```

At 1.5 g people carry less and walk slower, so stores run lower, but `half_full` still keeps all
30 alive on seed 1. At half the sunlight food grows less, and 12 of 30 die in the first year.
The knobs are `world.gravity`, `world.sunlight`, `world.rain` and `world.tilt` (see
`schema/lab-knobs.schema.json` for ranges). A value outside the tested range still runs but is
tagged `beyond-model`; a value outside the allowed range is refused with a message. Every
change is recorded in the run, and `--set` games are tagged `exploratory`.

**Twin worlds.** `aimpire lab twin` runs the same seeds twice: once on Earth, once with your
change, with the same mind. It then shows where the two worlds first part, and how the
numbers differ:

```bash
uv run aimpire lab twin m0 --set world.gravity=900000 --mind rule:half_full --seeds 1-3 --years 2 --out ../runs/lab
```

It prints a first-divergence table per seed and the end-of-run differences, and writes
`twin.md` with charts into the folder it names. At 0.9 g, for example, foragers bring in more
per day (they carry more), so stores end higher, while survival is unchanged for `half_full`.
Twin runs are exploration: a result counts only after a pre-registered re-run.

## 6. Play with a model on your laptop (free) **needs Ollama**

Install [Ollama](https://ollama.com), then fetch the model the example profile names:

```bash
ollama pull qwen3:8b
```

**Before any game, qualify the model.** `qualify` shows it six fixed situations and checks that
its replies are well formed (free here, and quick):

```bash
uv run aimpire qualify ../profiles/ollama-example.toml          # needs Ollama
```

It prints `PASS` or `FAIL` and writes a report in `runs/qualify-.../qualify.md`. Then play a
short game:

```bash
uv run aimpire run m0 --mind ../profiles/ollama-example.toml --seed 1 --years 1   # needs Ollama
```

A year is 12 councils; on a laptop each takes from a few seconds to a minute. The outputs are the
same as for a rule, and the notebook's Outcomes table now matters: it shows how many of the
model's replies were valid.

You can try `qualify` on the rules too (free, no Ollama). `uv run aimpire qualify rule` passes.
`uv run aimpire qualify rule:half_full` prints `FAIL`, and that is expected: that rule never
gives one-off orders, so the "order validity" check has nothing to measure.

## 7. Play with a paid model **needs a key**

Keys are never written in a file. Put the key in an environment variable in the terminal you
are using; it lasts until you close that terminal.

**Anthropic (Claude Haiku 4.5):**

```bash
export ANTHROPIC_API_KEY="paste-your-key-here"
uv run aimpire qualify ../profiles/anthropic-haiku-4-5.toml                       # needs a key
uv run aimpire run m0 --mind ../profiles/anthropic-haiku-4-5.toml --seed 1 --years 1   # needs a key
```

Without the key, nothing is called and you get a clear message instead:

```text
error: profile 'anthropic-haiku-4-5' needs the environment variable ANTHROPIC_API_KEY to hold its API key; it is not set
```

**OpenRouter:** copy `profiles/openrouter-template.toml` to a new name, for example
`profiles/openrouter-mine.toml`, and follow the three steps written at its top (model id and
both prices from the model's OpenRouter page). Then:

```bash
export OPENROUTER_API_KEY="paste-your-key-here"
uv run aimpire qualify ../profiles/openrouter-mine.toml                          # needs a key
uv run aimpire run m0 --mind ../profiles/openrouter-mine.toml --seed 1 --years 1      # needs a key
```

## 8. Money: the cost guard

- **Free:** every `rule:...` mind, `mock`, and Ollama (it runs on your machine). The guard still
  prints a line for them, with $0.
- **Paid:** Anthropic and OpenRouter profiles. Each profile states its price per million tokens.
- **Before anything is called**, every command prints the worst case, what is left this month,
  and the cap per run:

  ```text
  worst-case cost $11.692800 (largest run $0.389760); left this month $20.000000, run cap $1.000000
  ```

- **Caps:** $20 a month across all runs, and $2 a run unless the profile sets less. If the
  worst case does not fit, the command refuses and exits with code 3: nothing is called and
  nothing is spent.
- **The worst case is pessimistic:** it assumes every reply is as long as allowed. Real cost
  is usually a third or less. A 1-year Haiku game has a worst case of $0.34.
- **The spend is counted** from the runs in the runs folder. Set a hard monthly limit on each
  provider's own dashboard as well; that is the second lock.

## 9. Run an experiment

An experiment is a file in `experiments/` that says in advance what will be run and what it
should show. The free E0 dry run plays the whole design with stand-in minds:

```bash
uv run aimpire batch ../experiments/e0-dry-run.yaml --out runs/e0-dry
uv run aimpire batch ../experiments/e0-dry-run.yaml --out runs/e0-dry --verify
```

The first writes 48 games and a report in `runs/e0-dry/e0-dry-run/report.md`. The second checks
that neither the file nor its [pre-registration](../experiments/e0-preregistration.md) changed
after the games; it says "the experiment file matches every recorded run".

The live E0 files are listed in the pre-registration with their cost; read its sections 8 and 9
before running one. The [M0 reference bands](../experiments/m0-reference.md) page shows how the
four rules fare over 200 worlds; it is remade (free, about a quarter of an hour) with:

```bash
uv run aimpire batch ../experiments/m0-reference.yaml --out ../docs/experiments --jobs 2
```

## 10. Clean up

Everything a game writes is in `sim/runs/`. Git ignores that folder, so you can delete it
whenever you like.
