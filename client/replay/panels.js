// Aimpire replay player, side panels for aimpire-replay-v2 files (F4d).
// Plain browser JavaScript: no build step, no framework, no libraries.
//
// * Small-multiple sparklines (Tufte): one per measure, the same time axis,
//   zero-based, a direct label with the value at the time cursor. Pointer
//   down or drag on any of them moves the cursor.
// * A council strip on the same time axis: one mark per council, coloured by
//   outcome; a click selects that council.
// * The council panel: the mind's journal, annal, messages, names and beliefs
//   are shown verbatim as quoted data (textContent only, never parsed as
//   HTML); the policy and orders exactly as the decision record holds them.
"use strict";

(function () {
  const H = 30; // sparkline height, CSS px
  const SERIES = [
    { key: "population", label: "people", sub: "alive", div: 1 },
    { key: "stores_mu", label: "stores", sub: "food units", div: 1000 },
    { key: "near_camp_mu", label: "wild food", sub: "near camp, units", div: 1000 },
    { key: "deaths", label: "deaths", sub: "so far", div: 1 },
  ];
  const BAD = new Set(["INVALID", "REFUSAL", "TRUNCATED", "TIMEOUT", "PROVIDER_ERROR", "BUDGET"]);
  const fmt = (n) => Math.round(n).toLocaleString("en-US");

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // Index of the last entry of sorted ``ticks`` at or before ``tick`` (0 if none).
  function atOrBefore(ticks, tick) {
    let lo = 0, hi = ticks.length - 1, best = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (ticks[mid] <= tick) { best = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return best;
  }

  // ``opts``: {replay, onSeek(tick), onCouncil(index)}. Returns {update(tick, councilIndex)}.
  function charts(root, opts) {
    const { replay } = opts;
    const series = replay.series;
    const lastTick = replay.frames[replay.frames.length - 1].tick || 1;
    const rows = [];
    root.replaceChildren();
    root.append(el("h2", "", "Over time"));
    for (const spec of SERIES) {
      const col = series.columns.indexOf(spec.key);
      if (col < 0) continue;
      const values = series.values[col].map((v) => v / spec.div);
      const max = Math.max(...values, 1e-9);
      const row = el("div", "spark");
      const label = el("div", "label", spec.label);
      label.append(el("small", "", spec.sub));
      const plot = el("div", "plot");
      const value = el("div", "value");
      const now = el("span", "", "");
      value.append(now, el("small", "", `max ${fmt(max)}`));
      row.append(label, plot, value);
      root.append(row);
      rows.push({ spec, values, max, plot, value: now, path: "", width: 0 });
    }
    const bar = el("div", "spark");
    bar.id = "councilbar";
    const barLabel = el("div", "label", "councils");
    barLabel.append(el("small", "", "click to read"));
    const barPlot = el("div", "plot");
    const barCount = el("div", "value muted", `${replay.councils.length}`);
    bar.append(barLabel, barPlot, barCount);
    root.append(bar);

    const widthOf = (node) => Math.max(40, node.clientWidth || 300);
    const xOf = (tick, w) => (tick / lastTick) * w;
    const tickAt = (event, node) => {
      const box = node.getBoundingClientRect();
      const frac = Math.min(Math.max((event.clientX - box.left) / Math.max(box.width, 1), 0), 1);
      return Math.round(frac * lastTick);
    };

    for (const row of rows) {
      const seek = (e) => { if (e.buttons || e.type === "pointerdown") opts.onSeek(tickAt(e, row.plot)); };
      row.plot.addEventListener("pointerdown", seek);
      row.plot.addEventListener("pointermove", seek);
    }
    barPlot.addEventListener("click", (e) => {
      const tick = tickAt(e, barPlot);
      let best = 0;
      replay.councils.forEach((c, i) => {
        if (Math.abs(c.tick - tick) < Math.abs(replay.councils[best].tick - tick)) best = i;
      });
      if (replay.councils.length) opts.onCouncil(best);
    });

    function sparkPath(row, w) {
      if (row.width === w) return row.path;
      const y = (v) => (H - 1 - (v / row.max) * (H - 3)).toFixed(1);
      row.path = series.ticks.map((t, i) =>
        `${i ? "L" : "M"}${xOf(t, w).toFixed(1)} ${y(row.values[i])}`).join("");
      row.width = w;
      return row.path;
    }

    function update(tick, councilIndex) {
      const i = atOrBefore(series.ticks, tick);
      for (const row of rows) {
        const w = widthOf(row.plot);
        const x = xOf(series.ticks[i], w).toFixed(1);
        const v = row.values[i];
        const cy = (H - 1 - (v / row.max) * (H - 3)).toFixed(1);
        row.plot.innerHTML =
          `<svg viewBox="0 0 ${w} ${H}" preserveAspectRatio="none" role="img" ` +
          `aria-label="${row.spec.label} over time">` +
          `<line class="base" x1="0" x2="${w}" y1="${H - 0.5}" y2="${H - 0.5}"/>` +
          `<path class="series" d="${sparkPath(row, w)}"/>` +
          `<line class="cursor" x1="${x}" x2="${x}" y1="0" y2="${H}"/>` +
          `<circle class="dot" cx="${x}" cy="${cy}" r="2.5"/></svg>`;
        row.value.textContent = fmt(v);
      }
      const w = widthOf(barPlot);
      const marks = replay.councils.map((c, j) => {
        const x = xOf(c.tick, w).toFixed(1);
        const cls = j === councilIndex ? "sel" : BAD.has(c.outcome) ? "bad" : c.outcome;
        return `<line class="mk ${cls}" x1="${x}" x2="${x}" y1="5" y2="19"><title>council ` +
          `${c.council} · day ${c.tick} · ${c.outcome}</title></line>`;
      }).join("");
      const x = xOf(tick, w).toFixed(1);
      barPlot.innerHTML =
        `<svg viewBox="0 0 ${w} 22" preserveAspectRatio="none" role="img" aria-label="councils">` +
        `<rect class="hit" x="0" y="0" width="${w}" height="22"/>` +
        `<line class="base" x1="0" x2="${w}" y1="12" y2="12"/>${marks}` +
        `<line class="cursor" x1="${x}" x2="${x}" y1="0" y2="22"/></svg>`;
    }
    return { update };
  }

  function quote(parent, text, emptyText) {
    parent.append(text ? el("blockquote", "quote", text) : el("div", "empty", emptyText));
  }

  function placeLabel(place, names) {
    return names[place] ? `${place} “${names[place]}”` : place;
  }

  function section(parent, title) {
    parent.append(el("h3", "", title));
  }

  function table(parent, rows) {
    const t = el("table");
    for (const cells of rows) {
      const tr = el("tr");
      for (const [text, cls] of cells) tr.append(el("td", cls || "", text));
      t.append(tr);
    }
    parent.append(t);
  }

  // Fill ``root`` with council ``c`` (an entry of replay.councils). ``names``: place -> name.
  function council(root, c, names, nav) {
    root.replaceChildren();
    root.hidden = false;
    const head = el("div", "head");
    head.append(el("b", "", `Council ${c.council} · day ${c.tick}`),
      el("span", "muted", c.mind), el("span", c.outcome, c.outcome));
    const navBox = el("span", "nav");
    const prev = el("button", "", "‹ council");
    const next = el("button", "", "council ›");
    prev.type = next.type = "button";
    prev.addEventListener("click", nav.prev);
    next.addEventListener("click", nav.next);
    navBox.append(prev, next);
    head.append(navBox);
    root.append(head);
    root.append(el("div", "muted", `Decided on day ${c.tick}; in force from day ${c.tick + 1}.`));

    section(root, "Journal (verbatim)");
    quote(root, c.journal,
      BAD.has(c.outcome) ? "none: nothing from this reply was applied" : "not used");
    if (c.annal) { section(root, "Annal (verbatim)"); quote(root, c.annal, ""); }

    section(root, "Standing policy after this council");
    const lines = c.policy.allocations.map(([activity, place, share]) =>
      [[activity], [placeLabel(place, names)], [`${share}‰`, "r"]]);
    lines.push([["ration"], [""], [`${c.policy.ration}‰`, "r"]]);
    table(root, lines);

    if (c.orders.length) {
      section(root, "Orders");
      for (const o of c.orders) {
        const row = el("div", "order");
        row.append(el("span", "muted", `#${o.index} `), el("span", o.result, o.result));
        if (o.reason) row.append(el("span", "bad", ` ${o.reason}`));
        if (o.result === "ACCEPTED") {
          const [kind, place, target, qty, note] = o.order;
          row.append(el("div", "", `${kind} ${placeLabel(place, names)}` +
            `${qty ? ` · ${qty} people` : ""}${target ? ` · ${target}` : ""}`));
          if (note) quote(row, note, "");
        } else {
          row.append(el("div", "muted", o.order ? "as written:" : "not readable in the reply"));
          if (o.order) row.append(el("code", "", o.order));
        }
        root.append(row);
      }
    }
    if (c.messages.length) {
      section(root, "Messages (verbatim)");
      for (const [, to, text] of c.messages) {
        root.append(el("div", "muted", `to ${to}`));
        quote(root, text, "");
      }
    }
    if (c.names.length) {
      section(root, "Names given (verbatim)");
      table(root, c.names.map(([, id, name]) => [[id], [`“${name}”`]]));
    }
    if (c.beliefs.length) {
      section(root, "Beliefs (verbatim)");
      for (const [, statement, evidence] of c.beliefs) {
        quote(root, statement, "");
        root.append(el("div", "muted", `evidence: ${evidence.join(", ") || "none"}`));
      }
    }
    const other = c.rejections.filter(([field]) => !/^orders\[\d+\]$/.test(field));
    if (other.length || c.flags.length) {
      section(root, "Refused or changed by the validator");
      table(root, [
        ...other.map(([field, reason]) => [[field || "the reply"], [reason, "bad"]]),
        ...c.flags.map(([field, flag]) => [[field], [flag]]),
      ]);
    }
  }

  globalThis.AimpirePanels = { charts, council, atOrBefore };
})();
