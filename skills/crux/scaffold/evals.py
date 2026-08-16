#!/usr/bin/env python3
"""Agent evals for crux — spec 10.

`selftest.py` asserts that the ENGINE is right. This asserts that the AGENTS are, and it does
so without ever running one.

    python evals.py --certify-all
    python evals.py --fixture audit-01 --submission runs.json [--json]

## The shape, and why it is this shape

Spec 10 asks for a harness that invokes a model K times and bands the distribution. That is,
item for item, spec 05's three unbuilt work items — a Runner, a Budget & stop, and an autonomy
envelope — pointed at a fixture instead of at a hypothesis. `.spec/README.md` says **"Do not
implement 05."** The loop is the risk, not the target.

So the harness **never invokes an agent**. It scores a *submitted* findings file: whoever ran
the agent — the PI, attended, in a chat session — writes the ids it reported to a JSON file, and
this module does set arithmetic against a hand-authored manifest. Everything spec 10 measures is
still measured. The model-invoking runner is PARKED, not flagged off: there is no `--spawn`, and
this module has no network import and no subprocess that is not `crux.py`, which
`selftest.run_agent_evals` asserts by reading this file's own source.

## Ground truth, and how it is kept true

A fixture is only ground truth if something other than the agent says what is in it. So:

  - the manifest (`PLANTED.md`) is hand-authored and reviewed;
  - `certify()` proves the manifest true by running the engine's own `validation_report` and
    comparing the emitted id set to the planted id set, exactly.

A fixture that drifts from its manifest goes red in `selftest` immediately, and no eval ever
grades against a stale ground truth. That is spec 10's anti-tautology rule made mechanical
rather than promised.

The defect key is **the id the engine already emits** — a node id (`h2`), or a namespaced key
(`wiki:<slug>`, `task:<file>`). Nobody matches a message. A fixture plants at most one defect
per id; two defects means two nodes.
"""
import os, re, sys, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

FIXTURES = os.path.join(os.path.dirname(HERE), "evals", "fixtures")

#: every manifest declares these. `oracle` names the engine function that certifies it;
#: `band` is the PI's pre-registered bar and ships `unset` until they have seen a distribution.
MANIFEST_FIELDS = ("fixture", "agent", "ground_truth", "oracle", "checks", "band", "k")

GROUND_TRUTH_VALUES = ("yes", "proxy")
BAND_UNSET = "unset"


# ----------------------------------------------------------------------------- manifests
def fixture_names(root=None):
    """Every fixture directory, sorted. A directory without a PLANTED.md is not a fixture."""
    root = root or FIXTURES
    if not os.path.isdir(root):
        return []
    return sorted(n for n in os.listdir(root)
                  if os.path.isfile(os.path.join(root, n, "PLANTED.md")))


def _csv(val):
    """`a, b, c` -> ['a','b','c']. The house idiom for a list in a flat-scalar frontmatter —
    the same one `sources:` and `refs:` already use, so no second YAML dialect appears."""
    return [x.strip() for x in str(val or "").split(",") if x.strip()]


def _table(body, heading):
    """Rows of the first markdown table under `## <heading>`, as lists of stripped cells.

    The header row and the `|---|` rule are dropped. Pure — no filesystem access."""
    rows, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == heading.lower()
            continue
        if not in_sec:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            rows = []                      # the rule line: everything before it was the header
            continue
        rows.append(cells)
    return rows


def load_manifest(name, root=None):
    """Parse one fixture's PLANTED.md. Raises CruxError on anything malformed, because a
    manifest the harness cannot read is a ground truth nobody can check."""
    root = root or FIXTURES
    path = os.path.join(root, name, "PLANTED.md")
    if not os.path.isfile(path):
        raise E.CruxError(f"fixture '{name}': no PLANTED.md at {path}")
    fm, body = E.parse_doc(E.read(path))
    missing = [k for k in MANIFEST_FIELDS if fm.get(k) in (None, "")]
    if missing:
        raise E.CruxError(f"fixture '{name}': manifest is missing {', '.join(missing)}")
    if str(fm["ground_truth"]) not in GROUND_TRUTH_VALUES:
        raise E.CruxError(f"fixture '{name}': ground_truth must be one of "
                          f"{'/'.join(GROUND_TRUTH_VALUES)}, got '{fm['ground_truth']}'")
    planted = []
    for r in _table(body, "Planted"):
        if len(r) < 3:
            raise E.CruxError(f"fixture '{name}': planted row needs id | tier | class: {r}")
        planted.append({"id": r[0].strip("`"), "tier": r[1], "class": r[2],
                        "note": r[3] if len(r) > 3 else ""})
    if not planted:
        raise E.CruxError(f"fixture '{name}': no planted defects in the manifest")
    ids = [p["id"] for p in planted]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        # the constraint that buys exact scoring with no engine change: the id IS the key
        raise E.CruxError(f"fixture '{name}': two defects planted on one id ({', '.join(dup)}) "
                          f"— plant them in two nodes instead")
    return {"name": name, "dir": os.path.join(root, name), "fm": fm, "body": body,
            "agent": str(fm["agent"]), "ground_truth": str(fm["ground_truth"]),
            "oracle": str(fm["oracle"]), "checks": tuple(_csv(fm["checks"])),
            "band": str(fm["band"]), "k": int(fm["k"]), "planted": planted,
            "planted_ids": set(ids)}


def vault_of(manifest):
    return os.path.join(manifest["dir"], "vault")


# ----------------------------------------------------------------------------- certification
def emitted_ids(manifest):
    """The id set the engine reports on this fixture's vault, under the manifest's OWN
    `checks` list. Never a default: `gate` and `decks` are opt-in checks, so a certifier
    running the defaults would score a correctly-found gate backlog as invented."""
    r = E.validation_report(vault_of(manifest), checks=manifest["checks"])
    return {e["id"] for tier in ("problems", "warnings") for e in r[tier]}


def certify(name, root=None):
    """Prove the manifest true. Read-only; the fixture tree is never written.

    Three ways a hand-authored fixture goes wrong, and all three are caught here:
      missing — a planted id the engine does not emit (the defect was never planted, or was
                planted as something `validate` does not report at all: a task `blocked_by`
                cycle is a *status*, not a problem);
      extra   — an id the engine emits that nobody planted, which would score a CORRECT agent
                finding as invented;
      band    — `unset` is legal and reported, never silently treated as a pass."""
    m = load_manifest(name, root)
    got = emitted_ids(m)
    missing = sorted(m["planted_ids"] - got)
    extra = sorted(got - m["planted_ids"])
    return {"fixture": name, "agent": m["agent"], "ground_truth": m["ground_truth"],
            "ok": not missing and not extra, "missing": missing, "extra": extra,
            "planted": len(m["planted_ids"]), "band": m["band"],
            "band_set": m["band"] != BAND_UNSET}


def certify_all(root=None):
    return [certify(n, root) for n in fixture_names(root)]


# ----------------------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="evals.py", description="agent evals for crux (spec 10) — scores a submitted "
                                     "findings file; never invokes an agent")
    ap.add_argument("--certify-all", action="store_true",
                    help="prove every fixture's manifest against the engine, and stop")
    ap.add_argument("--fixture", help="the fixture to score against")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args(argv)

    if a.certify_all or not a.fixture:
        rows = certify_all()
        if a.json:
            print(json.dumps({"certified": rows}, indent=1))
        else:
            for r in rows:
                tag = "ok  " if r["ok"] else "FAIL"
                band = r["band"] if r["band_set"] else "band unset"
                print(f"  {tag} {r['fixture']:16} {r['planted']:2} planted  "
                      f"[{r['ground_truth']}]  {band}")
                for i in r["missing"]:
                    print(f"       missing: {i}")
                for i in r["extra"]:
                    print(f"       extra:   {i}")
        return 0 if all(r["ok"] for r in rows) else 1

    r = certify(a.fixture)
    print(json.dumps(r, indent=1) if a.json else r)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
