# crux cockpit benchmark harness

The repeatable measurement kit behind spec 12's performance numbers
([.spec/12-cockpit-craft.md](../../.spec/12-cockpit-craft.md)). Dev tooling only —
nothing here ships in the skill, is served by the cockpit, or runs in CI. Thresholds
live in the spec and its PRDs; these tools **report numbers**, they don't judge them.

## Contents

| file | what it does |
|---|---|
| `paint_probe.js` | console-paste probe. Part A: interaction timings (selection latency, search-typing rebuild count, hover repeat cost) — works on a hidden tab. Part B: paint battery (idle / hover-sweep / zoom-churn fps, worst frame, longtasks, with CSS ablations for attribution) — needs a **visible, foregrounded** tab. |
| `grow_vault.py` | grows a scratch vault with synthetic nodes through the real crux CLI (format-valid by construction). Seeded → reproducible. |
| `agent_writes.py` | edits one node at 1 Hz (`prose` or `vstate` mode) so the "idle under agent writes < 5% of a core" criterion can be measured. Restores the file on exit. |
| `baselines/` | committed result JSONs, one per ruling/PR — see naming rule below. |

## Procedure

1. **Never a real vault.** Copy one:
   `cp -R skills/crux/examples/demo_vault /tmp/benchvault`
2. Optional — grow it to stress size (330 drawn nodes ≈ 28×10 synthetic):
   `python3 tools/bench/grow_vault.py /tmp/benchvault 28 10`
3. Serve it: `python3 skills/crux/scaffold/crux.py serve --dir /tmp/benchvault --no-open`
4. Open the printed URL in the browser under test and **foreground the tab**
   (Part B refuses `document.hidden`; Part A runs regardless and says so).
5. Paste the whole of `paint_probe.js` into the devtools console. ~40 s later the
   result JSON is printed and copied to the clipboard.
6. For the agent-writes criterion: run
   `python3 tools/bench/agent_writes.py /tmp/benchvault --seconds 60`
   while the cockpit is open; record server CPU (`ps -o %cpu -p <pid>`) and the
   browser's own CPU for the tab (browser task manager).

## Recording a baseline (the env rule)

Absolute numbers are only comparable within one environment. Every saved run **must**
carry: browser + version, DPR, vault identity, drawn-node / SVG-element / text-run
counts (the probe records all of these in `env`). File name:
`baselines/YYYY-MM-DD-<browser><ver>-<vault><drawnNodes>.json`.

Safari note: `longtask` observers don't exist there — the probe degrades to fps +
worst frame, which is the signal that matters. Safari is where the original lag was
reported and was **not** covered by the 2026-08-15 Chrome gate run; prefer measuring
both when a change touches paint.

## The committed reference points

- `baselines/2026-08-15-chrome151-perfvault330.json` — the paint-profiling gate run
  (pre-fix `main`) that the PI's backdrop-filter ruling was made on: idle 60.3 fps
  clean; hover sweep 54.8 fps / 216.5 ms worst; zoom churn 49.6 ms worst; either
  ablation (no-spotlight or no-blur) restores ~60 fps / ~17 ms.
