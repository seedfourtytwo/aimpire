// Headless smoke test for the replay player (F4b, F4d). Node only, no dependencies.
//
// Runs map.js, panels.js and player.js against a small stand-in for the DOM, twice:
//
// 1. fixtures/wander.json (aimpire-replay-v1): steps to the last frame and
//    checks that the food layer and dots it draws equal
//    aimpire.report.frames.frame_array for the same tick. The expected SHA-256
//    of those RGB bytes comes from Python:
//
//      node client/replay/smoke-test.cjs "$(cd sim && uv run python scripts/make_fixture_replay.py --frame-sha256)"
//
// 2. fixtures/m0.json (aimpire-replay-v2, the default): checks the header,
//    the sparklines, the council panel (the journal and messages verbatim, as
//    text, from the fixture's own councils), council markers, and keys.
"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const here = __dirname;
const expected = process.argv[2];
assert.match(expected || "", /^[0-9a-f]{64}$/, "pass the expected frame SHA-256");

// --- a minimal DOM ---------------------------------------------------------------
class Node {
  constructor(tag, page) {
    this.tagName = tag.toUpperCase();
    this.page = page;
    this.children = [];
    this.handlers = {};
    this.ownText = "";
    this.innerHTML = "";
    this.className = "";
    this.hidden = false;
    this.style = {};
    this.value = "0";
    this.max = "0";
    this.width = 1;
    this.height = 1;
    this.clientWidth = 300;
  }
  get textContent() { return this.ownText + this.children.map((c) => c.textContent).join(""); }
  set textContent(text) { this.ownText = String(text); this.children = []; }
  append(...nodes) {
    for (const n of nodes) {
      if (typeof n === "string") this.ownText += n;
      else { n.parentElement = this; this.children.push(n); }
    }
  }
  replaceChildren() { this.children = []; this.ownText = ""; }
  addEventListener(type, fn) { (this.handlers[type] = this.handlers[type] || []).push(fn); }
  fire(type, event) { (this.handlers[type] || []).forEach((fn) => fn({ target: this, ...event })); }
  click() { this.fire("click", {}); }
  getBoundingClientRect() { return { left: 0, top: 0, width: 300, height: 30 }; }
  all() { return [this, ...this.children.flatMap((c) => c.all())]; }
  getContext() {
    const page = this.page;
    const target = {
      createImageData: (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
      putImageData: (img) => { page.lastImage = img; },
    };
    // Every other drawing call is accepted and counted.
    return new Proxy(target, {
      get: (t, key) => (key in t ? t[key] : () => { page.calls += 1; }),
      set: (t, key, v) => { t[key] = v; return true; },
    });
  }
}

const IDS = ["meta", "runid", "view", "key", "play", "back", "step", "slider", "speed",
  "status", "work", "charts", "council", "file"];

async function open(search) {
  const page = { lastImage: null, calls: 0, keydown: [] };
  const byId = {};
  const section = new Node("section", page);
  for (const id of IDS) {
    byId[id] = new Node(id === "view" ? "canvas" : "div", page);
    byId[id].id = id;
  }
  byId.view.parentElement = section;
  byId.speed.value = "5";
  const sandbox = {
    console, URLSearchParams, Math, Number, String, Error, JSON, Set, Object, Array, Proxy,
    setInterval, clearInterval,
    location: { search },
    window: { innerHeight: 800, devicePixelRatio: 1, addEventListener: () => {} },
    document: {
      getElementById: (id) => byId[id],
      createElement: (tag) => new Node(tag, page),
      documentElement: { clientWidth: 900 },
      addEventListener: (type, fn) => { if (type === "keydown") page.keydown.push(fn); },
    },
    fetch: async (src) => ({
      ok: true,
      json: async () => JSON.parse(fs.readFileSync(path.join(here, src), "utf8")),
    }),
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  for (const file of ["map.js", "panels.js", "player.js"]) {
    vm.runInContext(fs.readFileSync(path.join(here, file), "utf8"), sandbox, { filename: file });
  }
  await new Promise((resolve) => setTimeout(resolve, 50));
  page.$ = (id) => byId[id];
  page.key = (key) => page.keydown.forEach((fn) => fn({ key, target: section, preventDefault() {} }));
  return page;
}

function rgbSha(image) {
  const rgb = Buffer.alloc((image.data.length / 4) * 3);
  for (let i = 0, j = 0; i < image.data.length; i += 4, j += 3) {
    rgb[j] = image.data[i];
    rgb[j + 1] = image.data[i + 1];
    rgb[j + 2] = image.data[i + 2];
  }
  return crypto.createHash("sha256").update(rgb).digest("hex");
}

async function testV1() {
  const page = await open("?src=fixtures/wander.json");
  const { $ } = page;
  assert.match($("meta").textContent, /fixtures\/wander\.json · seed 42 .* 61 frames/);
  assert.match($("status").textContent, /^day 0 /);
  const last = Number($("slider").max);
  $("slider").fire("input", { target: { value: String(last) } });
  assert.match($("status").textContent, /^day 60 /);
  assert.equal(rgbSha(page.lastImage), expected, "player pixels differ from aimpire.report.frames");
  assert.equal($("charts").children.length, 0, "a v1 file has no charts");
  assert.equal($("council").hidden, true, "no council panel for v1");
  console.log(`player smoke test ok (v1): ${last + 1} frames, final frame matches Python pixels`);
}

async function testV2() {
  const replay = JSON.parse(fs.readFileSync(path.join(here, "fixtures/m0.json"), "utf8"));
  const page = await open("");
  const { $ } = page;
  const meta = $("meta").textContent;
  for (const part of ["C1: mock", `seed ${replay.run_seed}`, `rules ${replay.rules_version}`]) {
    assert.ok(meta.includes(part), `header lacks ${part}: ${meta}`);
  }
  assert.ok($("runid").textContent.startsWith(replay.run.run_id));
  assert.match($("status").textContent, /^day 0 · year 0 · season 0 · frame 1 of 7/);
  assert.ok(page.calls > 50, "the map overlay drew nothing");

  // Sparklines: one per measure, with the value at the cursor as a direct label.
  const charts = $("charts").all();
  const svgs = charts.filter((n) => n.innerHTML.startsWith("<svg"));
  assert.equal(svgs.length, 5, "four sparklines and the council strip");
  assert.ok(svgs.slice(0, 4).every((n) => n.innerHTML.includes('class="series"')));
  const text = $("charts").textContent;
  for (const label of ["people", "stores", "wild food", "deaths", "councils"]) {
    assert.ok(text.includes(label), `charts lack ${label}`);
  }
  assert.ok(text.includes("30"), "population at day 0 is shown");

  // Council panel at frame 0: council 1's journal, verbatim and as text.
  const first = replay.councils[0];
  assert.ok(first.journal.includes('"like these", <angle brackets> & accents (é)'));
  const panel = () => $("council").all();
  const journal = panel().find((n) => n.tagName === "BLOCKQUOTE");
  assert.equal(journal.textContent, first.journal, "journal not shown verbatim");
  assert.equal(journal.innerHTML, "", "mind text must never go through innerHTML");
  assert.ok($("council").textContent.includes("Council 1 · day 0"));
  assert.ok($("council").textContent.includes(`${first.policy.ration}‰`));

  // Step to day 30, whose map shows council 3 (held on day 20) at work: one accepted
  // and two rejected orders, and a message.
  page.key("ArrowRight");
  page.key("ArrowRight");
  assert.match($("status").textContent, /^day 20 /);
  assert.ok($("council").textContent.includes("Council 2 · day 10"), "day 20 shows council 2");
  page.key("ArrowRight");
  assert.match($("status").textContent, /^day 30 /);
  const third = replay.councils[2];
  const panelText = $("council").textContent;
  assert.ok(panelText.includes("Council 3 · day 20") && panelText.includes(third.journal));
  assert.ok(panelText.includes("ACCEPTED") && panelText.includes("REJECTED UNKNOWN_ENTITY"));
  assert.ok(panelText.includes("REJECTED UNKNOWN_ACTION"));
  assert.ok(panelText.includes(third.orders[1].order), "a rejected order is shown as written");
  assert.ok(panelText.includes(third.messages[0][2]), "messages are shown verbatim");
  assert.ok($("work").textContent.startsWith("C1 today:"));

  // Clicking the council strip near day 40 selects council 5 (not JSON: INVALID) and
  // moves to the first frame after it.
  const strip = $("charts").all().find((n) => n.innerHTML.includes('aria-label="councils"'));
  strip.fire("click", { clientX: Math.round((300 * 40) / 60) });
  assert.match($("status").textContent, /^day 50 /);
  assert.ok($("council").textContent.includes("Council 5 · day 40"));
  assert.ok($("council").textContent.includes("INVALID"));
  assert.ok($("council").textContent.includes("PARSE_FAILED"));

  // Keys: space plays and pauses, the left arrow steps back.
  page.key(" ");
  assert.equal($("play").textContent, "Pause");
  page.key(" ");
  assert.equal($("play").textContent, "Play");
  page.key("ArrowLeft");
  assert.match($("status").textContent, /^day 40 /);
  assert.ok($("council").textContent.includes("Council 4 · day 30"));
  console.log(`player smoke test ok (v2): ${replay.frames.length} frames, ` +
    `${replay.councils.length} councils, panels render`);
}

testV1().then(testV2).catch((err) => {
  console.error(err);
  process.exit(1);
});
