// Aimpire replay player for aimpire-replay-v2 and -v1 files (F4b, F4d; ADR-0010).
// Plain browser JavaScript: no build step, no framework, no libraries.
//
// The food layer is drawn one pixel per tile into an offscreen canvas, then
// enlarged by an integer factor without smoothing, so tiles stay crisp
// squares. Its colours use the same integer formula as aimpire.report.frames,
// so the layer matches the PNG frames rendered in Python pixel for pixel.
// On top, for v2 files, map.js draws the place borders, the camp and where
// today's workers went; panels.js draws the charts and the council panel.
"use strict";

(function () {
  const FORMATS = ["aimpire-replay-v1", "aimpire-replay-v2"];
  const DEFAULT_SRC = "fixtures/m0.json";
  const { INK, ACTIVE, rleDecode, layout, overlay, namesAt } = globalThis.AimpireMap;
  const $ = (id) => document.getElementById(id);
  const P = () => globalThis.AimpirePanels;
  const canvas = $("view");
  const ctx = canvas.getContext("2d");
  const tiles = document.createElement("canvas");
  const tilesCtx = tiles.getContext("2d");
  let replay = null, v2 = false, index = 0, timer = null, scale = 1;
  let geom = null, chartView = null, councilPick = null;

  // Integer ramp, identical to frames.layer_rgb: all operands are small non-negative ints.
  function rampColour(value, pal, scaleMax) {
    const clipped = Math.min(Math.max(value, 0), scaleMax);
    const level = Math.floor((clipped * 255) / scaleMax);
    return [0, 1, 2].map((k) =>
      Math.floor((pal.ramp_low[k] * (255 - level) + pal.ramp_high[k] * level) / 255));
  }

  function check(doc) {
    if (!doc || !FORMATS.includes(doc.format)) throw new Error(`not an ${FORMATS.join(" or ")} file`);
    if (!Array.isArray(doc.frames) || doc.frames.length === 0) throw new Error("no frames");
    const [rows, cols] = doc.grid;
    if (!(rows > 0 && cols > 0)) throw new Error("bad grid");
  }


  function fitScale() {
    const [rows, cols] = replay.grid;
    const box = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
    const width = Math.min(box || document.documentElement.clientWidth - 32, 560);
    const height = Math.max(window.innerHeight * 0.75, 160);
    // Whole CSS pixels per tile when there is room for 4 or more; below that the
    // map fills the width (tiles may then differ by a device pixel).
    const fit = Math.min(width / cols, height / rows);
    scale = Math.max(1, fit >= 4 ? Math.floor(fit) : fit);
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(cols * scale * dpr);
    canvas.height = Math.round(rows * scale * dpr);
    canvas.style.width = `${cols * scale}px`;
    canvas.style.height = `${rows * scale}px`;
  }


  // A council held on day T is committed before day T's step, so its policy is
  // first at work in the frame of day T + 1. The frame of day T therefore goes
  // with the latest council held before day T (the first council at day 0).
  function latestCouncil(tick) {
    let found = replay.councils.length ? 0 : -1;
    replay.councils.forEach((c, i) => { if (c.tick < tick) found = i; });
    return found;
  }

  function workLine(frame) {
    const parts = [];
    for (const civ of frame.civs) {
      const by = {};
      let working = 0;
      for (const [activity, , n] of civ.work) { by[activity] = (by[activity] || 0) + n; working += n; }
      const away = civ.trips.filter((t) => ACTIVE.has(t[4])).reduce((sum, t) => sum + t[3], 0);
      const rest = Math.max(0, civ.population - working - away);
      const shown = Object.keys(by).sort().map((a) => `${by[a]} ${a.toLowerCase()}`);
      if (away) shown.push(`${away} on order trips`);
      shown.push(`${rest} not assigned`);
      parts.push(`${civ.civ_id} today: ${shown.join(" · ")}`);
    }
    return parts.join("  |  ");
  }

  function draw() {
    const [rows, cols] = replay.grid;
    const frame = replay.frames[index];
    const pal = replay.palette;
    const img = tilesCtx.createImageData(cols, rows);
    const put = (cell, rgb) => {
      img.data.set(rgb, cell * 4);
      img.data[cell * 4 + 3] = 255;
    };
    rleDecode(frame.layer).forEach((v, cell) => put(cell, rampColour(v, pal, replay.scale_max)));
    for (const [, kind, row, col] of frame.dots) {
      put(row * cols + col, pal.kinds[replay.kinds.indexOf(kind)]);
    }
    tilesCtx.putImageData(img, 0, 0);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tiles, 0, 0, canvas.width, canvas.height);
    const cal = replay.calendar;
    const perYear = cal.ticks_per_season * cal.seasons_per_year;
    const season = Math.floor(frame.tick / cal.ticks_per_season) % cal.seasons_per_year;
    $("slider").value = String(index);
    $("status").textContent =
      `day ${frame.tick} · year ${Math.floor(frame.tick / perYear)} · season ${season} · ` +
      `frame ${index + 1} of ${replay.frames.length}`;
    if (!v2) {
      $("status").textContent += ` · ${frame.dots.length} dots · hash ${frame.hash.slice(0, 12)}`;
      return;
    }
    overlay(ctx, replay, frame, { ...geom, scale, dpr: window.devicePixelRatio || 1 });
    $("work").textContent = workLine(frame);
    const pick = councilPick !== null ? councilPick : latestCouncil(frame.tick);
    chartView.update(frame.tick, pick);
    if (pick >= 0) {
      P().council($("council"), replay.councils[pick], namesAt(frame), {
        prev: () => showCouncil(Math.max(pick - 1, 0)),
        next: () => showCouncil(Math.min(pick + 1, replay.councils.length - 1)),
      });
    }
  }

  function chip(parent, text, cls) {
    const span = document.createElement("span");
    if (cls) span.className = cls;
    span.textContent = text;
    parent.append(span);
    return span;
  }

  function showMeta(label) {
    const meta = $("meta");
    meta.replaceChildren();
    const cal = replay.calendar;
    if (v2) {
      const run = replay.run;
      for (const [seat, mind] of run.minds) chip(meta, `${seat}: ${mind}`, "mind");
      chip(meta, `seed ${replay.run_seed}`);
      chip(meta, `rules ${replay.rules_version} ${replay.rules_hash.slice(0, 8)}`);
      for (const o of run.overrides) chip(meta, o);
      for (const t of run.tags) chip(meta, t, "tag");
      chip(meta, `${replay.frames[replay.frames.length - 1].tick} days, a council every ` +
        `${run.council_every}; a year is ${cal.ticks_per_season * cal.seasons_per_year} days`);
      $("runid").textContent = `${run.run_id} · ${label}`;
      $("key").innerHTML =
        `<i style="color:${INK.FORAGE}"></i>foragers <i style="color:${INK.SCOUT}"></i>scouts ` +
        `<i style="color:${INK.trip};border-top-style:dashed"></i>order trips · ` +
        "number = people · lines are faint place borders · green = wild food on the tile";
    } else {
      chip(meta, `${label} · seed ${replay.run_seed} · rules ${replay.rules_version} · ` +
        `${replay.layer} 0–${replay.scale_max} · ${replay.frames.length} frames`);
      replay.kinds.forEach((kind, i) => {
        chip(meta, `■ ${kind}`).style.color = `rgb(${replay.palette.kinds[i].join(",")})`;
      });
      $("runid").textContent = "";
      $("key").textContent = "an aimpire-replay-v1 file: map only";
    }
  }

  function showCouncil(i) {
    stop();
    councilPick = i;
    const tick = replay.councils[i].tick;
    const frame = replay.frames.findIndex((f) => f.tick > tick); // first frame it acts in
    index = frame < 0 ? replay.frames.length - 1 : frame;
    draw();
  }

  function seekTick(tick) {
    let best = 0;
    replay.frames.forEach((f, i) => {
      if (Math.abs(f.tick - tick) < Math.abs(replay.frames[best].tick - tick)) best = i;
    });
    stop();
    goTo(best);
  }

  function load(doc, label) {
    check(doc);
    stop();
    replay = doc;
    v2 = doc.format === "aimpire-replay-v2";
    index = 0;
    councilPick = null;
    $("slider").max = String(doc.frames.length - 1);
    tiles.width = doc.grid[1];
    tiles.height = doc.grid[0];
    geom = v2 ? layout(doc) : null;
    $("work").textContent = "";
    $("council").hidden = true;
    $("charts").replaceChildren();
    chartView = v2 ? P().charts($("charts"), {
      replay: doc, onSeek: seekTick, onCouncil: showCouncil }) : null;
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
    councilPick = null;
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
  window.addEventListener("resize", () => {
    if (!replay) return;
    fitScale();
    draw();
  });
  document.addEventListener("keydown", (e) => {
    const tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (e.key === " ") {
      if (tag === "BUTTON") return; // the browser clicks a focused button itself
      e.preventDefault();
      $("play").click();
    }
    if (e.key === "ArrowRight") { e.preventDefault(); $("step").click(); }
    if (e.key === "ArrowLeft") { e.preventDefault(); $("back").click(); }
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
