/* crux cockpit bench probe — spec 12's repeatable harness (tools/bench/).
 *
 * Paste the whole file into the devtools console of a cockpit tab
 * (Chrome or Safari). Two parts:
 *
 *   Part A — interaction timings (JS + style/layout; works even on a hidden
 *            tab): renderTree()/layout() call counters, selection latency,
 *            a scripted 10-char search-typing driver, hover repeat cost.
 *   Part B — paint battery (REQUIRES a visible, foregrounded tab): idle /
 *            hover-sweep / zoom-churn fps + worst frame + longtasks, with
 *            injected-CSS ablations of the two historical suspects
 *            (spotlight transitions, backdrop-filter) for attribution.
 *
 * Prints a table and puts the JSON on the clipboard. Touches no source: all
 * instrumentation is monkey-patching + injected <style>, fully removed after.
 * Thresholds live in .spec/12-cockpit-craft.md, not here — this reports.
 * Record env with every saved run (see tools/bench/README.md, baselines/).
 */
(async () => {
  const svg = document.getElementById("tree");
  if (!svg) { console.error("no #tree svg — is this the cockpit?"); return; }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const q = (s) => [...svg.querySelectorAll(s)];
  const flush = () => void document.body.offsetHeight;   // force style+layout
  const ms = (t0) => +(performance.now() - t0).toFixed(2);
  const pct = (a, p) => a.slice().sort((x, y) => x - y)[Math.min(a.length - 1, Math.floor(a.length * p))] || 0;

  const out = { env: {
    ua: navigator.userAgent, dpr: devicePixelRatio, hidden: document.hidden,
    drawnNodes: q(".node").length, svgEls: svg.querySelectorAll("*").length,
    textRuns: q("text").length,
  } };

  /* ---------------- Part A — interaction timings (hidden-tab safe) -------- */
  // Call counters via monkey-patch. Works only if the functions are globals
  // (they are: app.js is a plain top-level script).
  const counters = {};
  const patched = [];
  for (const name of ["renderTree", "layout", "renderDetail", "applyCosmeticState"]) {
    if (typeof window[name] !== "function") continue;   // pre-P1 builds lack the helper
    const orig = window[name];
    counters[name] = 0;
    window[name] = function (...a) { counters[name]++; return orig.apply(this, a); };
    patched.push([name, orig]);
  }
  const resetCounters = () => Object.keys(counters).forEach((k) => (counters[k] = 0));
  const snapCounters = () => ({ ...counters });

  // A1 — selection latency: select every Nth node, measure selectNode incl. a
  // forced style+layout flush. Reported both end-to-end and tree-side
  // (end-to-end minus a same-selection renderDetail re-run) per ruling P-D7.
  if (typeof selectNode === "function") {
    const ids = q(".node").map((el) => el.getAttribute("data-id"));
    const stride = Math.max(1, Math.floor(ids.length / 25));
    const e2e = [];
    resetCounters();
    for (let i = 0; i < ids.length; i += stride) {
      const t0 = performance.now();
      selectNode(ids[i]);
      flush();
      e2e.push(performance.now() - t0);
    }
    // tree-side estimate: renderDetail alone on the already-selected node
    const det = [];
    for (let i = 0; i < 10 && typeof renderDetail === "function"; i++) {
      const t0 = performance.now(); renderDetail(); flush(); det.push(performance.now() - t0);
    }
    out["select"] = {
      n: e2e.length,
      e2eP50: +pct(e2e, 0.5).toFixed(2), e2eMax: +Math.max(...e2e).toFixed(2),
      detailP50: +pct(det, 0.5).toFixed(2),
      treeSideP50: +(pct(e2e, 0.5) - pct(det, 0.5)).toFixed(2),   // P-D7: the ruled criterion
      renderTreeCalls: snapCounters().renderTree || 0,             // spec: must be 0
    };
  }

  // A2 — search typing driver: type a 10-char word one keystroke at a time
  // (real input events, so any debounce runs as shipped), then count rebuilds.
  {
    const box = document.getElementById("search");
    const word = "imputation";
    box.value = ""; box.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(400);
    resetCounters();
    const t0 = performance.now();
    for (const ch of word) {
      box.value += ch;
      box.dispatchEvent(new Event("input", { bubbles: true }));
      flush();
      await sleep(30);   // ~33 cps, a fast typist
    }
    await sleep(400);    // let any trailing debounce fire
    out["search10"] = {
      wallMs: ms(t0) - 400,
      renderTreeCalls: snapCounters().renderTree || 0,   // spec: ≤ 2 (expected 0 post-P1)
      cosmeticCalls: snapCounters().applyCosmeticState || 0,
    };
    box.value = "";
    box.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(300);
  }

  // A3 — hover repeat cost: 12 pointerovers on ONE node (what crossing its 12
  // child elements fires). Post-fix the same-node guard makes 11 of them free:
  // repeat12/first ≈ 1. Also the live-animation count after one hover.
  {
    const el = q(".node")[Math.floor(q(".node").length / 2)];
    const fire = () => { el.dispatchEvent(new PointerEvent("pointerover", { bubbles: true })); flush(); };
    svg.dispatchEvent(new PointerEvent("pointerout", { bubbles: true })); flush();
    let t0 = performance.now(); fire(); const first = performance.now() - t0;
    t0 = performance.now(); for (let i = 0; i < 11; i++) fire(); const rest11 = performance.now() - t0;
    const anims = document.getAnimations ? document.getAnimations().length : -1;
    svg.dispatchEvent(new PointerEvent("pointerout", { bubbles: true })); flush();
    out["hoverRepeat"] = {
      firstMs: +first.toFixed(2), rest11Ms: +rest11.toFixed(2),
      repeatRatio: +((rest11 / 11) / (first || 1e-9)).toFixed(2),  // ≈0 when guarded
      liveAnimationsAfterHover: anims,
    };
  }

  for (const [name, orig] of patched) window[name] = orig;   // un-patch

  /* ---------------- Part B — paint battery (visible tab only) ------------- */
  if (document.hidden) {
    console.warn("tab is hidden — Part B (paint/fps) skipped. Foreground the tab and rerun for paint numbers.");
  } else {
    function fpsProbe(dur) {
      return new Promise((res) => {
        let frames = 0, worst = 0, last = performance.now(), lt = 0, ltMax = 0, po = null;
        try {
          po = new PerformanceObserver((l) => l.getEntries().forEach((e) => {
            lt++; ltMax = Math.max(ltMax, e.duration);
          }));
          po.observe({ entryTypes: ["longtask"] });
        } catch (e) { /* Safari: no longtask — fps + worst frame still meaningful */ }
        const t0 = performance.now();
        (function tick(t) {
          if (t !== undefined) { frames++; worst = Math.max(worst, t - last); last = t; }
          if (performance.now() - t0 < dur) requestAnimationFrame(tick);
          else {
            if (po) po.disconnect();
            const dt = (performance.now() - t0) / 1000;
            res({ fps: +(frames / dt).toFixed(1), worstFrameMs: +worst.toFixed(1),
                  longtasks: lt, worstLongtaskMs: +ltMax.toFixed(0) });
          }
        })();
      });
    }
    const nodes = q(".node");
    function hoverDriver() {
      let i = 0;
      const iv = setInterval(() => {
        const el = nodes[(i++ * 7) % nodes.length]; // stride: consecutive targets aren't neighbours
        const r = el.getBoundingClientRect();
        el.dispatchEvent(new PointerEvent("pointerover",
          { bubbles: true, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 }));
      }, 30); // ~33 crossings/s ≈ a fast mouse sweep
      return () => clearInterval(iv);
    }
    function zoomDriver() {
      const r = svg.getBoundingClientRect();
      const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
      let n = 0, dir = 1;
      const iv = setInterval(() => {
        if (++n % 24 === 0) dir = -dir;
        svg.dispatchEvent(new WheelEvent("wheel",
          { bubbles: true, cancelable: true, clientX: cx, clientY: cy, deltaY: dir * 40 }));
      }, 16);
      return () => clearInterval(iv);
    }
    const inject = (id, css) => { const s = document.createElement("style"); s.id = id; s.textContent = css; document.head.appendChild(s); };
    const remove = (id) => { const s = document.getElementById(id); if (s) s.remove(); };
    // Ablations neutralize BOTH the pre-P2 (.node.cold) and post-P2 (#tree.spot)
    // dim forms, so attribution runs are comparable across the fix boundary.
    const NOSPOT = ".node{transition:none !important}" +
      ".node.cold,#tree.spot .node{opacity:1 !important}.edge{transition:none !important}";
    const NOBLUR = "*{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}";

    async function scenario(driver, ablations) {
      ablations.forEach((a, i) => inject("probe-abl-" + i, a));
      await sleep(250);
      const stop = driver ? driver() : null;
      await sleep(200);
      const r = await fpsProbe(4000);
      if (stop) stop();
      r.liveAnimations = document.getAnimations ? document.getAnimations().length : -1;
      svg.dispatchEvent(new PointerEvent("pointerout", { bubbles: true }));
      ablations.forEach((_, i) => remove("probe-abl-" + i));
      await sleep(500);
      return r;
    }
    console.log("probe: idle baseline…");
    out["idle"] = await fpsProbe(2000);
    const matrix = [
      ["hover:baseline",     hoverDriver, []],
      ["hover:no-spotlight", hoverDriver, [NOSPOT]],
      ["hover:no-blur",      hoverDriver, [NOBLUR]],
      ["hover:both-off",     hoverDriver, [NOSPOT, NOBLUR]],
      ["zoom:baseline",      zoomDriver,  []],
      ["zoom:no-blur",       zoomDriver,  [NOBLUR]],
      ["zoom:no-spotlight",  zoomDriver,  [NOSPOT]],
      ["zoom:both-off",      zoomDriver,  [NOSPOT, NOBLUR]],
    ];
    for (const [name, driver, abl] of matrix) {
      console.log("probe:", name);
      out[name] = await scenario(driver, abl);
    }
  }

  console.table(out);
  const json = JSON.stringify(out, null, 1);
  try { await navigator.clipboard.writeText(json); console.log("→ JSON copied to clipboard"); }
  catch (e) { console.log("→ clipboard blocked; copy the object above:", json); }
  return out;
})();
