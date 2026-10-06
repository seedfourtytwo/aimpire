#!/usr/bin/env python3
"""Cut the Aimpire concept trailer: shots + crisp UI overlays + ambient pad.

Inputs: clips/s1.mp4 … clips/s8.mp4 (from generate.py). Output: aimpire-trailer.mp4.
Overlays are drawn with Pillow (not generated), so every word on screen is exact.
    python3 assemble.py            # final cut
    python3 assemble.py --test     # use coloured placeholder clips
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
W, H, FPS, XF = 1920, 1080, 24, 0.5           # crossfade seconds
BUILD = HERE / "build"
def _font_file(style):
    """Find Inter (fc-match); fall back to DejaVu Sans so the cut still renders."""
    for q in (f"Inter:style={style}", f"Inter {style}"):
        r = subprocess.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True)
        if r.returncode == 0 and "Inter" in r.stdout:
            return r.stdout
    print(f"warning: Inter {style} not found; install the Inter font for the intended look")
    r = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans"], capture_output=True, text=True)
    return r.stdout
_FONTS = {}
def font(style, size):
    if style not in _FONTS: _FONTS[style] = _font_file(style)
    return ImageFont.truetype(_FONTS[style], size)

WHITE, DIM, AMBER, TEAL, OCHRE = (245, 242, 235), (190, 186, 178), (240, 176, 80), (90, 200, 190), (214, 150, 70)


# ---------- overlay drawing -------------------------------------------------
def canvas(): return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def shadowed(img, xy, text, f, fill=WHITE, anchor="la"):
    sh = canvas(); ImageDraw.Draw(sh).text(xy, text, font=f, fill=(0, 0, 0, 200), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill, anchor=anchor)

def caption(text, y=H - 120):
    img = canvas(); shadowed(img, (W // 2, y), text, font("Medium", 46), anchor="ma"); return img

def panel(img, box, radius=14):
    d = ImageDraw.Draw(img); d.rounded_rectangle(box, radius, fill=(14, 16, 20, 190), outline=(255, 255, 255, 40), width=1)

def journal():
    img = canvas(); panel(img, (80, 80, 860, 250)); d = ImageDraw.Draw(img)
    d.text((110, 105), "COUNCIL · REED CAMP · DAY 40", font=font("SemiBold", 22), fill=OCHRE)
    d.text((110, 145), "“The east grove is thinning.", font=font("Italic", 34), fill=WHITE)
    d.text((110, 190), "Send four to the river flats.”", font=font("Italic", 34), fill=WHITE)
    return img

def channel_bar(active="SIGN"):
    img = canvas(); labels = ["SIGN · RAIN", "OMEN", "VOICE", "PRAYER"]
    f = font("SemiBold", 26); d = ImageDraw.Draw(img); y = H - 210
    ws = [int(d.textlength(l, font=f)) + 48 for l in labels]; tot = sum(ws) + 18 * (len(ws) - 1)
    x = (W - tot) // 2; panel(img, (x - 20, y - 20, x + tot + 20, y + 64), 16); d = ImageDraw.Draw(img)
    for lab in labels:
        w = int(d.textlength(lab, font=f)) + 48
        on = lab.startswith(active)
        d.rounded_rectangle((x, y, x + w, y + 44), 10, fill=(240, 176, 80, 235) if on else (255, 255, 255, 18),
                            outline=None if on else (255, 255, 255, 60))
        d.text((x + 24, y + 8), lab, font=f, fill=(20, 18, 14) if on else DIM); x += w + 18
    return img

def voice_box(typed, heard=None):
    img = canvas(); panel(img, (W - 900, 80, W - 80, 300 if heard else 230)); d = ImageDraw.Draw(img)
    d.text((W - 870, 105), f"VOICE → ONE PERSON: AMA, REED CAMP", font=font("SemiBold", 22), fill=AMBER)
    d.text((W - 230, 105), f"{len(typed)}/280", font=font("Regular", 22), fill=DIM)
    d.text((W - 870, 150), typed + ("▍" if len(typed) < 44 else ""), font=font("Regular", 32), fill=WHITE)
    if heard:
        d.text((W - 870, 215), "HEARD", font=font("SemiBold", 22), fill=DIM)
        d.text((W - 870, 245), heard, font=font("Italic", 32), fill=AMBER)
    return img

def trace(n_lit, concluded=False):
    img = canvas(); steps = ["sent", "heard", "reported", "concluded", "done"]
    f = font("Medium", 28); x0 = 150; y = 110
    panel(img, (110, 70, W - 110, 245 if concluded else 175)); d = ImageDraw.Draw(img)
    gap = (W - 2 * x0) // (len(steps) - 1)
    for i, s in enumerate(steps):
        x = x0 + i * gap; lit = i < n_lit
        if i: d.line((x - gap + 18, y, x - 18, y), fill=(240, 176, 80, 220) if lit else (255, 255, 255, 50), width=3)
        d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=AMBER if lit else (60, 60, 60, 200))
        d.text((x, y + 22), s, font=f, fill=WHITE if lit else DIM, anchor="ma")
    if concluded:
        d.text((W // 2, 195), "concluded:  “The sky tells us to cross.”", font=font("Italic", 30), fill=AMBER, anchor="ma")
    return img

def card(lines, sizes=None, colors=None, gap=26):
    img = Image.new("RGBA", (W, H), (6, 7, 9, 255)); d = ImageDraw.Draw(img)
    sizes = sizes or [64] * len(lines); colors = colors or [WHITE] * len(lines)
    fonts = [font("Medium", s) for s in sizes]
    total = sum(s for s in sizes) + gap * (len(lines) - 1); y = (H - total) // 2
    for t, fo, c, s in zip(lines, fonts, colors, sizes):
        d.text((W // 2, y), t, font=fo, fill=c, anchor="ma"); y += s + gap
    return img

def title():
    img = Image.new("RGBA", (W, H), (6, 7, 9, 255)); d = ImageDraw.Draw(img)
    word, f = "AIMPIRE", font("SemiBold", 150); sp = 38
    widths = [d.textlength(ch, font=f) for ch in word]; x = (W - (sum(widths) + sp * (len(word) - 1))) / 2
    for ch, w in zip(word, widths): d.text((x, 330), ch, font=f, fill=WHITE); x += w + sp
    d.text((W // 2, 560), "Untrained AI sandbox.", font=font("Regular", 46), fill=WHITE, anchor="ma")
    d.text((W // 2, 625), "Tribes evolving in an infinitely generative universe.", font=font("Regular", 46), fill=WHITE, anchor="ma")
    d.text((W // 2, 860), "Concept trailer, not gameplay   ·   Open source   ·   github.com/seedfourtytwo/aimpire",
           font=font("Regular", 26), fill=DIM, anchor="ma")
    return img


# ---------- timeline --------------------------------------------------------
# (segment, clip or None, length s, [(overlay image, start, end)])
def timeline():
    V = "Wait for the river to fall before you cross."
    return [
        ("open1", None, 2.2, [(card(["Every god game gave you followers."], [60]), 0, 99)]),
        ("open2", None, 2.2, [(card(["We gave them minds."], [72]), 0, 99)]),
        ("s1", "s1", 6.5, [(caption("Generated worlds. Their own physics."), 2.0, 99)]),
        ("s2", "s2", 7.5, [(journal(), 0.8, 99), (caption("Their council is a model. It sees only what its people saw."), 3.0, 99)]),
        ("dev", None, 3.2, [(card(["Minds propose.", "A deterministic world decides.", "Every run replays."], [54, 54, 54],
                                  [WHITE, WHITE, AMBER]), 0, 99)]),
        ("s3", "s3", 6.5, [(channel_bar(), 0.5, 99), (caption("You cannot command. Only influence.", 120), 2.5, 99)]),
        ("s4", "s4", 7.5, [(voice_box(V[:17]), 0.6, 1.4), (voice_box(V[:31]), 1.4, 2.2), (voice_box(V), 2.2, 4.0),
                           (voice_box(V, "“… the river … cross …”"), 4.0, 99)]),
        ("s5", "s5", 7.5, [(trace(1), 0.4, 1.4), (trace(2), 1.4, 2.4), (trace(3), 2.4, 3.4), (trace(4, True), 3.4, 5.2),
                           (trace(5, True), 5.2, 99), (caption("They decide what you meant."), 4.0, 99)]),
        ("s6", "s6", 7.5, [(caption("Generations remember. Records drift."), 0.6, 3.8),
                           (caption("A second tribe. A different model."), 4.0, 99)]),
        ("s7", "s7", 7.0, [(caption("Every civilization meets the Great Filter."), 1.8, 99)]),
        ("s8", "s8", 6.5, [(caption("Many worlds. One day, they meet."), 1.5, 99)]),
        ("title", None, 6.5, [(title(), 0, 99)]),
    ]


def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def segment(name, clip, length, overlays, clipdir):
    out = BUILD / f"{name}.mp4"; inputs, filt = [], []
    if clip:
        inputs += ["-ss", "0.3", "-t", str(length), "-i", str(clipdir / f"{clip}.mp4")]
        filt.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuva420p[b0]")
        audio = ["-map", "0:a?"]
    else:
        inputs += ["-f", "lavfi", "-t", str(length), "-i", f"color=c=0x060709:s={W}x{H}:r={FPS}"]
        filt.append("[0:v]format=yuva420p[b0]"); audio = []
    last = "b0"
    for i, (img, t0, t1) in enumerate(overlays):
        p = BUILD / f"{name}_{i}.png"; img.save(p); inputs += ["-loop", "1", "-t", str(length), "-i", str(p)]
        t1 = min(t1, length); fo = min(0.35, (t1 - t0) / 3)
        filt.append(f"[{i+1}:v]format=rgba,fade=t=in:st={t0}:d={fo}:alpha=1"
                    + (f",fade=t=out:st={t1-fo}:d={fo}:alpha=1" if t1 < length else "") + f"[o{i}]")
        filt.append(f"[{last}][o{i}]overlay=0:0:enable='between(t,{t0},{t1})'[b{i+1}]"); last = f"b{i+1}"
    filt.append(f"[{last}]format=yuv420p[v]")
    a = ["-f", "lavfi", "-t", str(length), "-i", "anullsrc=r=48000:cl=stereo"]
    na = len(overlays) + 1
    amap = audio if clip else []
    cmd = ["ffmpeg", "-y", *inputs, *a, "-filter_complex", ";".join(filt), "-map", "[v]"]
    if clip:
        cmd += ["-filter_complex", f"[0:a]aresample=48000,apad[aa]"] if False else []
        cmd += ["-map", "0:a?"] if probe_audio(clipdir / f"{clip}.mp4") else ["-map", f"{na}:a"]
    else:
        cmd += ["-map", f"{na}:a"]
    cmd += ["-t", str(length), "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(out)]
    run(cmd); return out

def probe_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True); return bool(r.stdout.strip())


# ---------- ambient pad -----------------------------------------------------
def pad(seconds, path):
    sr = 48000; t = np.arange(int(seconds * sr)) / sr
    chords = [[146.83, 220.0, 329.63, 440.0], [130.81, 196.0, 293.66, 392.0], [116.54, 174.61, 261.63, 349.23], [146.83, 220.0, 293.66, 369.99]]
    seg = seconds / len(chords); sig = np.zeros((2, len(t)))
    for k, ch in enumerate(chords):
        env = np.clip(1 - np.abs((t - (k + 0.5) * seg) / (seg * 0.85)), 0, 1) ** 1.5
        for j, f0 in enumerate(ch):
            for side, det in ((0, -0.6), (1, 0.6)):
                ph = 2 * np.pi * (f0 + det) * t
                sig[side] += env * (np.sin(ph) + 0.25 * np.sin(2 * ph + 0.4 * np.sin(0.2 * t))) * (0.9 ** j)
    sig += 0.35 * np.sin(2 * np.pi * 73.42 * t) * np.clip(t / 6, 0, 1)            # low drone
    for side in (0, 1):                                                          # cheap reverb
        for d, g in ((0.113, 0.45), (0.271, 0.35), (0.389, 0.28), (0.541, 0.2)):
            n = int(d * sr * (1.07 if side else 1)); sig[side, n:] += g * sig[side, :-n]
    swell = np.clip((t - (seconds - 9)) / 5, 0, 1) * np.clip((seconds - t) / 2.5, 0, 1)
    sig *= (0.55 + 0.6 * swell) * np.clip(t / 2.5, 0, 1) * np.clip((seconds - t) / 2.0, 0, 1)
    sig /= np.abs(sig).max() * 1.12
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((sig.T * 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--test", action="store_true"); a = ap.parse_args()
    BUILD.mkdir(exist_ok=True); clipdir = HERE / "clips"
    if a.test:
        clipdir = BUILD / "fake"; clipdir.mkdir(exist_ok=True)
        for i in range(1, 9):
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc2=s=1920x1080:r=24:d=8", "-f", "lavfi", "-i",
                 f"sine=f={200+40*i}:d=8", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(clipdir / f"s{i}.mp4")])
    tl = timeline(); segs = []
    for name, clip, length, ov in tl:
        if clip and not (clipdir / f"{clip}.mp4").exists(): sys.exit(f"missing clip {clip}")
        segs.append((segment(name, clip, length, ov, clipdir), length)); print("built", name)
    # chain crossfades
    inputs = sum((["-i", str(p)] for p, _ in segs), []); fv, fa = [], []
    lv, la, off = "0:v", "0:a", 0.0
    for i in range(1, len(segs)):
        off += segs[i - 1][1] - XF
        fv.append(f"[{lv}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]"); lv = f"v{i}"
        fa.append(f"[{la}][{i}:a]acrossfade=d={XF}[a{i}]"); la = f"a{i}"
    total = off + segs[-1][1]
    pad(total, BUILD / "pad.wav"); inputs += ["-i", str(BUILD / "pad.wav")]; pi = len(segs)
    fa.append(f"[{la}]volume=0.75[sx];[{pi}:a]volume=0.55[pd];[sx][pd]amix=inputs=2:normalize=0,alimiter=limit=0.9[am]")
    out = HERE / ("trailer-test.mp4" if a.test else "aimpire-trailer.mp4")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fv + fa), "-map", f"[{lv}]", "-map", "[am]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "192k", str(out)])
    print(f"wrote {out.name}: {total:.1f}s")


if __name__ == "__main__":
    main()
