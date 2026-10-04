// Headless smoke test for the replay player (F4b). Node only, no dependencies.
//
// Runs player.js against a tiny stand-in for the DOM, lets it fetch the
// fixture replay, steps to the last frame and checks that the pixels it draws
// equal aimpire.report.frames.frame_array for the same tick. The expected
// SHA-256 of those RGB bytes comes from Python:
//
//   node client/replay/smoke-test.cjs "$(cd sim && uv run python scripts/make_fixture_replay.py --frame-sha256)"
"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const here = __dirname;
const expected = process.argv[2];
assert.match(expected || "", /^[0-9a-f]{64}$/, "pass the expected frame SHA-256");

let lastImage = null;
const elements = {};
function element(id) {
  if (!elements[id]) {
    const handlers = {};
    elements[id] = {
      id, textContent: "", value: "0", max: "0", style: {}, width: 1, height: 1,
      addEventListener: (type, fn) => { (handlers[type] = handlers[type] || []).push(fn); },
      fire: (type, event) => (handlers[type] || []).forEach((fn) => fn(event)),
      click() { this.fire("click", {}); },
      append(...nodes) { nodes.forEach((n) => { this.textContent += n.textContent || n; }); },
      getContext: () => ({
        createImageData: (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
        putImageData: (img) => { lastImage = img; },
      }),
    };
  }
  return elements[id];
}

const sandbox = {
  console, URLSearchParams, Math, Number, String, Error, JSON,
  setInterval, clearInterval,
  location: { search: "" },
  window: { innerHeight: 600, addEventListener: () => {} },
  document: {
    getElementById: element,
    documentElement: { clientWidth: 800 },
    addEventListener: () => {},
    createElement: () => ({ style: {}, textContent: "" }),
  },
  HTMLInputElement: class {},
  HTMLSelectElement: class {},
  fetch: async (src) => ({
    ok: true,
    json: async () => JSON.parse(fs.readFileSync(path.join(here, src), "utf8")),
  }),
};

vm.runInNewContext(fs.readFileSync(path.join(here, "player.js"), "utf8"), sandbox);

setTimeout(() => {
  const meta = element("meta").textContent;
  assert.match(meta, /fixtures\/wander\.json · seed 42 .* 61 frames/, meta);
  assert.match(element("status").textContent, /^tick 0 /);
  const last = Number(element("slider").max);
  element("slider").fire("input", { target: { value: String(last) } });
  assert.match(element("status").textContent, /^tick 60 /);
  const rgb = Buffer.alloc((lastImage.data.length / 4) * 3);
  for (let i = 0, j = 0; i < lastImage.data.length; i += 4, j += 3) {
    rgb[j] = lastImage.data[i];
    rgb[j + 1] = lastImage.data[i + 1];
    rgb[j + 2] = lastImage.data[i + 2];
  }
  const actual = crypto.createHash("sha256").update(rgb).digest("hex");
  assert.equal(actual, expected, "player pixels differ from aimpire.report.frames");
  console.log(`player smoke test ok: ${last + 1} frames, final frame matches Python pixels`);
}, 50);
