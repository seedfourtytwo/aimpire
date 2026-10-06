#!/usr/bin/env python3
"""Generate the Aimpire concept-trailer shots with Veo 3.1 through OpenRouter.

Stdlib only. Needs OPENROUTER_API_KEY in the environment (never pass it on the
command line). Each shot is 8 s at 1080p with sound at $0.40/s = $3.20.

    python3 generate.py --dry-run          # show plan and cost, spend nothing
    python3 generate.py                    # generate every shot not yet in clips/
    python3 generate.py --only s4 --retake # regenerate one shot with a new seed

A ledger (spent.json) records every submitted job; the script refuses any
submission that would take the total past --cap (default $35).
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

API = "https://openrouter.ai/api/v1"
MODEL = "google/veo-3.1"
SECONDS, RESOLUTION, PRICE_PER_S = 8, "1080p", 0.40
HERE = Path(__file__).resolve().parent
CLIPS, LEDGER = HERE / "clips", HERE / "spent.json"


def call(method, path, body=None, raw=False):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json",
                 # In a Claude cloud environment with an API credential, the agent
                 # proxy attaches the key itself; locally, the env var is used.
                 **({"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]}
                    if os.environ.get("OPENROUTER_API_KEY") else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if raw else json.loads(data)


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"jobs": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="shot ids, e.g. s1 s4")
    ap.add_argument("--retake", action="store_true", help="regenerate even if a clip exists, new seed")
    ap.add_argument("--cap", type=float, default=35.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="free: confirm the key works and the live price")
    a = ap.parse_args()

    if a.check:
        models = call("GET", "/videos/models")
        items = models.get("data", models) if isinstance(models, dict) else models
        veo = [m for m in items if isinstance(m, dict) and m.get("id") == MODEL]
        print(json.dumps(veo[0] if veo else {"error": f"{MODEL} not listed"}, indent=1)[:1500])
        print(f"Script assumes ${PRICE_PER_S}/s with audio. Stop if the live price is higher.")
        return
    shots = json.loads((HERE / "shots.json").read_text())
    if a.only:
        shots = [s for s in shots if s["id"] in a.only]
    CLIPS.mkdir(exist_ok=True)
    todo = [s for s in shots if a.retake or not (CLIPS / f"{s['id']}.mp4").exists()]
    led = ledger()
    spent = sum(j["cost"] for j in led["jobs"])
    cost = len(todo) * SECONDS * PRICE_PER_S
    print(f"{len(todo)} shot(s) × {SECONDS}s × ${PRICE_PER_S}/s = ${cost:.2f}; "
          f"already spent ${spent:.2f}; cap ${a.cap:.2f}")
    if spent + cost > a.cap + 1e-9:
        sys.exit("Refusing: this would exceed the cap.")
    if a.dry_run or not todo:
        return

    jobs = {}
    for s in todo:
        seed = s["seed"] + (1000 * (1 + sum(j["shot"] == s["id"] for j in led["jobs"])) if a.retake else 0)
        body = {"model": MODEL, "prompt": s["prompt"], "duration": SECONDS,
                "resolution": RESOLUTION, "aspect_ratio": "16:9",
                "generate_audio": True, "seed": seed}
        try:
            r = call("POST", "/videos", body)
        except urllib.error.HTTPError as e:
            print(f"{s['id']}: submit failed {e.code}: {e.read()[:300]!r}")
            continue
        jid = r.get("id") or r.get("job_id")
        led["jobs"].append({"shot": s["id"], "job": jid, "seed": seed,
                            "cost": SECONDS * PRICE_PER_S, "at": time.time()})
        LEDGER.write_text(json.dumps(led, indent=1))
        jobs[s["id"]] = jid
        print(f"{s['id']}: submitted {jid} (seed {seed})")

    while jobs:
        time.sleep(15)
        for sid, jid in list(jobs.items()):
            st = call("GET", f"/videos/{jid}")
            status = st.get("status")
            if status == "completed":
                data = call("GET", f"/videos/{jid}/content?index=0", raw=True)
                out = CLIPS / f"{sid}.mp4"
                if out.exists():
                    out.rename(CLIPS / f"{sid}.take{int(time.time())}.mp4")
                out.write_bytes(data)
                print(f"{sid}: done → {out.name} ({len(data)//1024} KB)")
                del jobs[sid]
            elif status == "failed":
                print(f"{sid}: FAILED {json.dumps(st)[:400]}")
                del jobs[sid]
    print("All jobs finished. Ledger:", LEDGER)


if __name__ == "__main__":
    main()
