// Aimpire replay player, the map overlay for aimpire-replay-v2 files (F4d).
// Plain browser JavaScript: no build step, no framework, no libraries.
//
// Drawn over the food layer, all from the frame's own ``civs`` record and the
// replay's ``places``: faint place borders with each place's id (and the
// civilization's own name for it), the camp, thin lines from the camp to where
// today's workers went with their number, and dashed lines for ordered trips
// still under way. Coordinates are canvas pixels; a tile is ``scale * dpr``.
"use strict";

(function () {
  // Overlay colours sit on the light food ramp in both themes, so they are fixed.
  const INK = { edge: "rgba(30,30,28,0.28)", label: "rgba(30,30,28,0.62)",
    FORAGE: "#22356f", SCOUT: "#b04a0c", trip: "#7a1f9c", camp: "#c81e1e" };
  const ACTIVE = new Set(["ORDERED", "EN_ROUTE", "RETURNING"]);

  // [value, count, value, count, ...] -> flat row-major list of values.
  function rleDecode(pairs) {
    const out = [];
    for (let i = 0; i < pairs.length; i += 2) {
      for (let n = 0; n < pairs[i + 1]; n++) out.push(pairs[i]);
    }
    return out;
  }

  // Tile edges where the place changes, [x1, y1, x2, y2] in tile units, and each
  // place's top-left tile [row, col] (where its label goes).
  function layout(doc) {
    const [rows, cols] = doc.grid;
    const owner = rleDecode(doc.places.tiles);
    const out = [];
    const corners = doc.places.ids.map(() => [rows, cols]);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const here = owner[r * cols + c];
        corners[here] = [Math.min(corners[here][0], r), Math.min(corners[here][1], c)];
        if (c + 1 < cols && owner[r * cols + c + 1] !== here) out.push([c + 1, r, c + 1, r + 1]);
        if (r + 1 < rows && owner[(r + 1) * cols + c] !== here) out.push([c, r + 1, c + 1, r + 1]);
      }
    }
    return { edges: out, corners };
  }

  // Centre of a place's centroid tile, in canvas pixels, nudged by (dx, dy) tiles.
  function at(replay, place, s, dx = 0, dy = 0) {
    const [r, c] = replay.places.centroids[replay.places.ids.indexOf(place)];
    return [(c + 0.5 + dx) * s, (r + 0.5 + dy) * s];
  }

  function line(ctx, from, to, colour, width, dash) {
    ctx.strokeStyle = colour;
    ctx.lineWidth = width;
    ctx.setLineDash(dash);
    ctx.beginPath();
    ctx.moveTo(from[0], from[1]);
    ctx.lineTo(to[0], to[1]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function disc(ctx, p, radius, fill, ring) {
    ctx.beginPath();
    ctx.arc(p[0], p[1], radius, 0, 2 * Math.PI);
    ctx.fillStyle = fill;
    ctx.fill();
    if (ring) { ctx.strokeStyle = ring; ctx.lineWidth = radius / 2.5; ctx.stroke(); }
  }

  function text(ctx, str, p, colour, px) {
    ctx.font = `${px}px system-ui, sans-serif`;
    ctx.fillStyle = colour;
    ctx.fillText(str, p[0], p[1]);
  }

  // Draw on ``ctx`` (canvas pixels): ``geom`` is {scale (CSS px per tile), dpr, edges, corners}.
  function overlay(ctx, replay, frame, geom) {
    const { scale, dpr, edges, corners } = geom;
    const s = scale * dpr, u = dpr; // u: one CSS pixel
    ctx.strokeStyle = INK.edge;
    ctx.lineWidth = u;
    ctx.beginPath();
    for (const [x1, y1, x2, y2] of edges) { ctx.moveTo(x1 * s, y1 * s); ctx.lineTo(x2 * s, y2 * s); }
    ctx.stroke();
    const names = namesAt(frame);
    // Labels sit in the top-left of each block: one line for the id, one for the
    // civilization's own name (cut to the block's width).
    replay.places.ids.forEach((id, i) => {
      const [r, c] = corners[i];
      const wide = (replay.places.centroids[i][1] - c) * 2 * scale;
      const room = Math.max(4, Math.floor(wide / 6) - 1);
      const x = c * s + 4 * u, y = r * s + 13 * u;
      text(ctx, id, [x, y], INK.label, 10 * u);
      if (names[id]) {
        const name = names[id].length > room ? `${names[id].slice(0, room - 1)}…` : names[id];
        text(ctx, name, [x, y + 12 * u], INK.label, 10 * u);
      }
    });
    for (const civ of frame.civs) {
      const home = at(replay, civ.camp, s);
      for (const [activity, place, n] of civ.work) {
        if (!n) continue;
        const to = at(replay, place, s, activity === "SCOUT" ? 2 : -2, 2);
        const colour = INK[activity] || INK.label;
        line(ctx, home, to, colour, 1.5 * u, []);
        disc(ctx, to, (2 + Math.sqrt(n)) * u, colour, null);
        // The count goes on the far side of the dot from the camp, off the line.
        const away = to[0] >= home[0] ? 1 : -1;
        ctx.textAlign = away > 0 ? "left" : "right";
        text(ctx, `${n}`, [to[0] + away * (5 + Math.sqrt(n)) * u, to[1] + 4 * u], colour, 11 * u);
        ctx.textAlign = "left";
      }
      for (const [, kind, place, qty, status] of civ.trips) {
        if (!ACTIVE.has(status)) continue;
        const to = at(replay, place, s, 0, -2);
        line(ctx, home, to, INK.trip, 1.5 * u, [4 * u, 3 * u]);
        text(ctx, `${qty} ${kind.toLowerCase()} trip`, [to[0] + 5 * u, to[1]], INK.trip, 11 * u);
      }
      if (civ.population > 0) {
        disc(ctx, home, 5 * u, INK.camp, "#ffffff");
        text(ctx, "camp", [home[0] + 8 * u, home[1] - 6 * u], INK.camp, 11 * u);
      }
    }
  }

  function namesAt(frame) {
    const out = {};
    for (const civ of frame.civs || []) for (const [place, name] of civ.names) out[place] = name;
    return out;
  }

  globalThis.AimpireMap = { INK, ACTIVE, rleDecode, layout, overlay, namesAt };
})();
