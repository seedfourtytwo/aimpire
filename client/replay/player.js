// Aimpire replay player for aimpire-replay-v1 files (F4b, ADR-0010).
// Plain browser JavaScript: no build step, no framework, no libraries.
//
// One canvas pixel is one tile. The canvas is enlarged by an integer factor
// with pixelated (nearest-neighbour) rendering, so tiles stay crisp squares.
// Colours use the same integer formula as aimpire.report.frames, so a frame
// here matches the PNG frames rendered in Python pixel for pixel.
"use strict";

(function () {
  const FORMAT = "aimpire-replay-v1";
  const DEFAULT_SRC = "fixtures/wander.json";
  const $ = (id) => document.getElementById(id);
  const canvas = $("view");
  const ctx = canvas.getContext("2d");
  let replay = null;
  let index = 0;
  let timer = null;

  // [value, count, value, count, ...] -> flat row-major list of values.
  function rleDecode(pairs) {
    const out = [];
    for (let i = 0; i < pairs.length; i += 2) {
      for (let n = 0; n < pairs[i + 1]; n++) out.push(pairs[i]);
    }
    return out;
  }

  // Integer ramp, identical to frames.layer_rgb: all operands are small non-negative ints.
  function rampColour(value, pal, scaleMax) {
    const clipped = Math.min(Math.max(value, 0), scaleMax);
    const level = Math.floor((clipped * 255) / scaleMax);
    return [0, 1, 2].map((k) =>
      Math.floor((pal.ramp_low[k] * (255 - level) + pal.ramp_high[k] * level) / 255));
  }

  function check(doc) {
    if (!doc || doc.format !== FORMAT) throw new Error(`not an ${FORMAT} file`);
    if (!Array.isArray(doc.frames) || doc.frames.length === 0) throw new Error("no frames");
    const [rows, cols] = doc.grid;
    if (!(rows > 0 && cols > 0)) throw new Error("bad grid");
  }

  function fitScale() {
    const [rows, cols] = replay.grid;
    const width = document.documentElement.clientWidth - 32;
    const height = Math.max(window.innerHeight * 0.7, 160);
    const scale = Math.max(1, Math.floor(Math.min(width / cols, height / rows)));
    canvas.style.width = `${cols * scale}px`;
    canvas.style.height = `${rows * scale}px`;
  }

  function draw() {
    const [rows, cols] = replay.grid;
    const frame = replay.frames[index];
    const pal = replay.palette;
    const img = ctx.createImageData(cols, rows);
    const put = (cell, rgb) => {
      img.data.set(rgb, cell * 4);
      img.data[cell * 4 + 3] = 255;
    };
    rleDecode(frame.layer).forEach((v, cell) => put(cell, rampColour(v, pal, replay.scale_max)));
    for (const [, kind, row, col] of frame.dots) {
      put(row * cols + col, pal.kinds[replay.kinds.indexOf(kind)]);
    }
    ctx.putImageData(img, 0, 0);
    const cal = replay.calendar;
    const season = Math.floor(frame.tick / cal.ticks_per_season) % cal.seasons_per_year;
    const year = Math.floor(frame.tick / (cal.ticks_per_season * cal.seasons_per_year));
    $("slider").value = String(index);
    $("status").textContent =
      `tick ${frame.tick} · year ${year} season ${season} · ` +
      `${frame.dots.length} dots · hash ${frame.hash.slice(0, 12)}`;
  }

  function showMeta(label) {
    const meta = $("meta");
    meta.textContent =
      `${label} · seed ${replay.run_seed} · rules ${replay.rules_version} · ` +
      `${replay.layer} 0–${replay.scale_max} · ${replay.frames.length} frames`;
    replay.kinds.forEach((kind, i) => {
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = `rgb(${replay.palette.kinds[i].join(",")})`;
      meta.append(swatch, kind);
    });
  }

  function load(doc, label) {
    check(doc);
    stop();
    replay = doc;
    index = 0;
    const slider = $("slider");
    slider.max = String(doc.frames.length - 1);
    canvas.width = doc.grid[1];
    canvas.height = doc.grid[0];
    showMeta(label);
    fitScale();
    draw();
  }

  function fail(message) {
    $("meta").textContent = message;
  }

  function goTo(i) {
    if (!replay) return;
    index = Math.min(Math.max(i, 0), replay.frames.length - 1);
    draw();
  }

  function stop() {
    if (timer !== null) clearInterval(timer);
    timer = null;
    $("play").textContent = "Play";
  }

  function play() {
    if (!replay) return;
    if (index >= replay.frames.length - 1) index = 0;
    const perSecond = Number($("speed").value);
    timer = setInterval(() => {
      if (index >= replay.frames.length - 1) stop();
      else goTo(index + 1);
    }, 1000 / perSecond);
    $("play").textContent = "Pause";
  }

  $("play").addEventListener("click", () => (timer === null ? play() : stop()));
  $("step").addEventListener("click", () => { stop(); goTo(index + 1); });
  $("back").addEventListener("click", () => { stop(); goTo(index - 1); });
  $("slider").addEventListener("input", (e) => { stop(); goTo(Number(e.target.value)); });
  $("speed").addEventListener("change", () => { if (timer !== null) { stop(); play(); } });
  window.addEventListener("resize", () => { if (replay) fitScale(); });
  document.addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
    if (e.key === " ") { e.preventDefault(); $("play").click(); }
    if (e.key === "ArrowRight") $("step").click();
    if (e.key === "ArrowLeft") $("back").click();
  });
  $("file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      load(JSON.parse(await file.text()), file.name);
    } catch (err) {
      fail(`cannot open ${file.name}: ${err.message}`);
    }
  });

  const src = new URLSearchParams(location.search).get("src") || DEFAULT_SRC;
  fetch(src)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((doc) => load(doc, src))
    .catch((err) => fail(`cannot load ${src}: ${err.message}. Use the file picker, ` +
      "or serve this folder over HTTP."));
})();
