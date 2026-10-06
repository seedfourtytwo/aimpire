# Handoff: generate the Aimpire concept trailer

**For:** a coding agent with `OPENROUTER_API_KEY` set in its environment.
**Goal:** a 60–65 s concept trailer, `aimpire-trailer.mp4`, that explains Aimpire to a developer. Eight AI-generated shots are cut together with exact UI overlays, title cards and an ambient soundtrack.
**Budget:** hard cap **$35** total on OpenRouter. Expected spend is **$25.60**, with room for at most two retakes.

## Read first

- `docs/pitch/trailer.md`: the creative brief. Story, shot list, overlays and the prompts, which are the source of `shots.json`.
- `docs/vision.md`: what Aimpire is. The trailer must not claim anything this page marks as not built, beyond what the brief already shows as concept.

## What is in this folder

| File | Purpose |
|---|---|
| `shots.json` | The 8 Veo prompts (id, name, prompt, seed). Each prompt ends with a shared style line. |
| `generate.py` | Submits shots to OpenRouter (`google/veo-3.1`, 8 s, 1080p, 16:9, audio on), polls the jobs and downloads to `clips/`. Every job is logged in `spent.json`, and the script refuses anything over the cap. Stdlib only. |
| `assemble.py` | Cuts `clips/s1–s8.mp4` into the trailer. Overlays are drawn with Pillow so every word is exact; adds crossfades and an ambient pad. `--test` runs on placeholder clips. |

## Requirements

Python 3.10+, `pip install pillow numpy`, `ffmpeg` and `ffprobe` on PATH, and the **Inter** font installed (`fc-match Inter` should find it). Without Inter the script falls back to DejaVu Sans and prints a warning.

## Rules

1. **Never write the key anywhere.** Not in files, logs, commits or chat. It is read only from the environment.
2. **Never exceed $35.** Check `spent.json` before every submission. If OpenRouter's live price differs from $0.40/s, stop and report.
3. **No dialogue or readable text in the generated clips.** All text comes from `assemble.py`. A clip with visible garbled letters, logos or watermarks counts as a failed take.
4. **The end card must keep the line "Concept trailer, not gameplay".**
5. Generated clips and the final video are deliverables, not repo content. `clips/`, `build/`, `spent.json` and `*.mp4` are git-ignored here.

## Steps

```bash
cd tools/trailer
python3 assemble.py --test          # 1. free: proves the edit pipeline and fonts on this machine
python3 generate.py --check         # 2. free: proves the key works and shows Veo 3.1's live price
python3 generate.py --dry-run       # 3. free: shows the plan and the cost
python3 generate.py --only s2       # 4. $3.20: one test shot. Review it before going on (see below)
python3 generate.py                 # 5. $22.40: the other seven shots (skips any clip already present)
python3 generate.py --only s4 --retake   # 6. only if needed, at most two retakes, $3.20 each
python3 assemble.py                 # 7. the final cut → aimpire-trailer.mp4
```

**Reviewing a shot.** Pull four frames and look at them:

```bash
for t in 1 3 5 7; do ffmpeg -v error -y -ss $t -i clips/s2.mp4 -frames:v 1 -vf scale=960:-1 build/s2_$t.jpg; done
```

Pass a shot if all of these hold:

- it matches its description in the brief;
- the god's-eye miniature look is consistent with the other shots;
- people are small and readable;
- there is no text, logo or watermark;
- there are no severe artefacts (melting bodies, flicker).

Also listen to the clip's sound: it must have no speech in a real language. Shot s5 asks for murmuring in an invented language.

**If s2 fails the look test,** adjust the shared style line in `shots.json` (the sentence starting "Style:") for all shots and say so in your report. Do not change the story.

## Done means

- `aimpire-trailer.mp4` exists: about 60–65 s, 1920×1080, H.264 with AAC audio, every overlay legible.
- A contact sheet (one frame per segment) and the final `spent.json` total are reported.
- The report lists any retakes, prompt changes and anything that looks off.

Send the video, the contact sheet and the report to the creator. Do not publish the video anywhere.
