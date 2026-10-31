#!/usr/bin/env python3
"""Self-test for spec 20 (anchoring): the `## Bears on` section and the CLI `--bears` flag,
the `validate` info line, the exploratory cap at moderate, `path` in brief and wrap, `review`
in wrap, the unchanged `status --json` key set, and the 4.0 -> 4.1 bump with no migration.

    python3 selftest_anchoring.py      # standalone: prints PASSED a / b, exits 1 on any failure

`run_all(check)` takes selftest.py's `check(name, cond)`. Every assert name starts with one
prefix (`anchor 1.1:` ... `anchor 1.7:`, `anchor 1.4-cli:`, `anchor ix:`), each mapping to an
acceptance item of .spec/20-anchoring.md. Written against the spec, before the engine: an
unknown kwarg or a missing function is a FAIL line, never a traceback. Every test runs in a
temp dir with HOME pointed into it; nothing committed is written."""
import os, sys, json, shutil, subprocess, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

CLI = os.path.join(HERE, "crux.py")
DEMO = os.path.abspath(os.path.join(HERE, "..", "examples", "demo_vault"))
_ERR = object()          # what _try returns when the call raised


# ------------------------------------------------------------------------------- helpers
def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _try(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception:
        return _ERR


def _raises(exc, fn, *a, **kw):
    """The exception instance when fn raises exactly `exc` (or a subclass), else None."""
    try:
        fn(*a, **kw)
    except exc as e:
        return e
    except Exception:
        return None
    return None


def _env(tmp):
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    env = dict(os.environ, HOME=home, USERPROFILE=home, CRUX_NO_UPDATE_CHECK="1")
    env.pop("CRUX_SWEEP", None)
    return env


def _cli(cwd, argv, env):
    return subprocess.run([sys.executable, CLI] + list(argv), cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def _json(r):
    try:
        return json.loads(r.stdout or "")
    except Exception:
        return None


def _vault(tmp, name):
    root = os.path.join(tmp, name)
    E.cmd_init("Anchor test " + name, root)
    return root


def _node(root, nid):
    return E.Vault(root).get(nid)


def _bears(root, nid):
    return E._section(_node(root, nid)["body"], "Bears on")


def _files(root, prefix):
    return sorted(fn for fn in os.listdir(root) if re.match(prefix + r"\d+_.*\.md$", fn))


def _counter(root, key):
    return int(E.Vault(root).cfg.get(key) or 0)


def _bears_path(root, nid):
    return E.bears_path(E.Vault(root), nid)


def _call(tid, cmd, session="s-now"):
    import selftest_capture as SC
    return SC._rec("assistant", [{"type": "tool_use", "id": tid, "name": "Bash",
                                  "input": {"command": cmd}}], session)


def _result(tid, text, session="s-now"):
    import selftest_capture as SC
    return SC._rec("user", [{"type": "tool_result", "tool_use_id": tid, "content": text,
                             "is_error": False}], session)


def _transcript(tmp, name, steps):
    """steps: [(command, id)] — each a successful tool call whose result names `id`."""
    import selftest_capture as SC
    body = SC._turns("Let us keep going on this.", "Noted.", "s-now")
    for i, (cmd, nid) in enumerate(steps):
        tid = "t%d" % i
        body += _call(tid, cmd) + _result(tid, json.dumps({"id": nid}))
    p = os.path.join(tmp, "home", ".claude", "projects", "anchor", name + ".jsonl")
    _write(p, body)
    return p


# ------------------------------------------------------------------------------- 1.1
def _cli_bears_tests(check, tmp):
    env = _env(tmp)
    root = _vault(tmp, "v11")
    q0, _ = E.cmd_ask(root, "Parent question")

    def refused(label, argv, prefix, counter):
        files, n = _files(root, prefix), _counter(root, counter)
        r = _cli(root, argv, env)
        check("anchor 1.1: %s exits 1" % label, r.returncode == 1)
        check("anchor 1.1: %s names --bears on stderr" % label, "--bears" in (r.stderr or ""))
        check("anchor 1.1: %s writes no file and allocates no id" % label,
              _files(root, prefix) == files and _counter(root, counter) == n)

    refused("ask without --bears", ["ask", "t"], "q", "counter_q")
    refused("hypothesize without --bears",
            ["hypothesize", "t", "-p", q0, "--expect", "e"], "h", "counter_h")
    refused("the alias q without --bears", ["q", "t"], "q", "counter_q")
    refused("ask with a blank --bears", ["ask", "t", "--bears", ""], "q", "counter_q")
    refused("hypothesize with a blank --bears",
            ["hypothesize", "t", "-p", q0, "--expect", "e", "--bears", "   "], "h", "counter_h")

    r = _cli(root, ["ask", "t", "--bears", "B", "--json"], env)
    out = _json(r) or {}
    check("anchor 1.1: ask with --bears exits 0", r.returncode == 0 and bool(out.get("id")))
    check("anchor 1.1: ... and writes `## Bears on` with the given text",
          bool(out.get("id")) and _try(_bears, root, out.get("id")) == "B")
    r = _cli(root, ["hypothesize", "t", "-p", q0, "--expect", "e", "--bears", "B", "--json"], env)
    out = _json(r) or {}
    check("anchor 1.1: hypothesize with --bears exits 0", r.returncode == 0 and bool(out.get("id")))
    check("anchor 1.1: ... and writes `## Bears on` with the given text",
          bool(out.get("id")) and _try(_bears, root, out.get("id")) == "B")


# ------------------------------------------------------------------------------- 1.2
SEED = """\
- Project: Seeded anchor — a seed with no bears lines
  - Q: Does approach A help?
    - H: A helps overall
      - expect: A beats the baseline by at least 0.01
"""


def _api_tests(check, tmp):
    root = _vault(tmp, "v12")
    r = _try(E.cmd_ask, root, "Plain question")
    q = r[0] if r is not _ERR else None
    check("anchor 1.2: cmd_ask without bears writes a question",
          q is not None and _node(root, q).type == "question")
    check("anchor 1.2: ... with no `## Bears on` heading",
          q is not None and "## Bears on" not in _read(_node(root, q)["path"]))
    r = _try(E.cmd_hypothesize, root, "Plain hypothesis", parent=q, expect="e")
    h = r[0] if r is not _ERR else None
    check("anchor 1.2: cmd_hypothesize without bears writes a hypothesis",
          h is not None and _node(root, h).type == "idea")
    check("anchor 1.2: ... with no `## Bears on` heading",
          h is not None and "## Bears on" not in _read(_node(root, h)["path"]))
    r = _try(E.cmd_hypothesize, root, "No expectation", parent=q, require_expect=False)
    check("anchor 1.2: cmd_hypothesize(require_expect=False) still writes",
          r is not _ERR and _node(root, r[0]).type == "idea")
    seed = os.path.join(tmp, "seed.md")
    _write(seed, SEED)
    sroot = os.path.join(tmp, "v12seed")
    r = _try(E.cmd_init_from, seed, sroot)
    sv = _try(E.Vault, sroot) if r is not _ERR else _ERR
    check("anchor 1.2: cmd_init_from with a seed that has no bears still materializes",
          sv is not _ERR and sum(1 for n in sv.nodes.values() if n.type == "question") == 1
          and sum(1 for n in sv.nodes.values() if n.type == "idea") == 1)

    r = _try(E.cmd_ask, root, "Anchored question", bears="B")
    qb = r[0] if r is not _ERR else None
    text = _read(_node(root, qb)["path"]) if qb else ""
    check("anchor 1.2: cmd_ask(bears=) writes `## Bears on` before `## Protocol`",
          "## Bears on" in text and "## Protocol" in text
          and text.index("## Bears on") < text.index("## Protocol")
          and _try(_bears, root, qb) == "B")
    r = _try(E.cmd_hypothesize, root, "Anchored hypothesis", parent=q, expect="e", bears="B")
    hb = r[0] if r is not _ERR else None
    text = _read(_node(root, hb)["path"]) if hb else ""
    heads = ("## Problem Statement", "## Bears on", "## Idea / Hypothesis")
    check("anchor 1.2: cmd_hypothesize(bears=) puts `## Bears on` between Problem Statement "
          "and Idea / Hypothesis",
          all(x in text for x in heads)
          and text.index(heads[0]) < text.index(heads[1]) < text.index(heads[2])
          and _try(_bears, root, hb) == "B")


# ------------------------------------------------------------------------------- 1.3
def _bears_entries(rep):
    return [i for i in rep.get("info", []) if i.get("id") == "boundary:bears-on"]


def _validate_tests(check, tmp):
    env = _env(tmp)
    clean = _vault(tmp, "v13clean")
    rep = E.validation_report(clean)
    check("anchor 1.3: a vault with no questions or hypotheses has no bears-on info",
          _bears_entries(rep) == [] and rep["ok"] is True)

    root = _vault(tmp, "v13")
    q1, _ = E.cmd_ask(root, "First question")
    q2, _ = E.cmd_ask(root, "Second question", parent=q1)
    h1, _, _ = E.cmd_hypothesize(root, "A hypothesis", parent=q1, expect="e")
    n = 3
    rep = E.validation_report(root)
    ents = _bears_entries(rep)
    check("anchor 1.3: validate reports one boundary:bears-on info entry", len(ents) == 1)
    check("anchor 1.3: ... counting every question and hypothesis without the section",
          len(ents) == 1 and ents[0].get("count") == n)
    check("anchor 1.3: ... whose message names `Bears on`",
          len(ents) == 1 and "Bears on" in ents[0].get("message", ""))
    check("anchor 1.3: ... and never as a problem or a warning",
          not any("bears" in json.dumps(x).lower() for x in rep["problems"] + rep["warnings"]))
    check("anchor 1.3: ... so `ok` stays True", rep["ok"] is True)
    r = _cli(root, ["validate", "--strict"], env)
    check("anchor 1.3: validate --strict exits 0 on items without `## Bears on`",
          r.returncode == 0)

    for nid in (q1, q2, h1):
        p = _node(root, nid)["path"]
        _write(p, _read(p).rstrip("\n") + "\n\n## Bears on\n\nB for %s.\n" % nid)
    rep = E.validation_report(root)
    check("anchor 1.3: once every item states its bears line, the entry is gone",
          _bears_entries(rep) == [] and rep["ok"] is True)


# ------------------------------------------------------------------------------- 1.4
def _exploratory_tests(check, tmp):
    root = _vault(tmp, "v14")
    q, _ = E.cmd_ask(root, "What does the data show?")
    q2, _ = E.cmd_ask(root, "Is the effect measured?")
    q3, _ = E.cmd_ask(root, "Is there a weak pattern?")
    q4, _ = E.cmd_ask(root, "Does A beat B?")
    h, _, _ = E.cmd_hypothesize(root, "A beats B", parent=q4, expect="A wins by 0.01")

    r = _try(E.cmd_finding, root, q, "strong", answer="a", exploratory=True)
    f = r[0] if r is not _ERR else None
    check("anchor 1.4: an exploratory strong finding returns a cap note",
          r is not _ERR and r[2] is not None)
    fm = _node(root, f)["fm"] if f else {}
    check("anchor 1.4: ... is stored as moderate", fm.get("confidence") == "moderate")
    check("anchor 1.4: ... with `exploratory: true` in its frontmatter",
          fm.get("exploratory") is True)
    st = _try(E.derive_state, E.Vault(root), q)
    check("anchor 1.4: ... so its question leans at moderate, not settled",
          st is not _ERR and st.get("state") == "leaning" and st.get("confidence") == "moderate")

    E.cmd_finding(root, q2, "strong", answer="a")
    st = E.derive_state(E.Vault(root), q2)
    check("anchor 1.4: a strong finding without the flag still settles its question",
          st.get("state") == "settled" and st.get("confidence") == "strong")

    r = _try(E.cmd_finding, root, q3, "weak", answer="a", exploratory=True)
    check("anchor 1.4: an exploratory weak finding stays weak with no note",
          r is not _ERR and r[2] is None and _node(root, r[0])["fm"].get("confidence") == "weak")

    if f:   # read side: a hand edit cannot raise the node past moderate
        p = _node(root, f)["path"]
        _write(p, _read(p).replace("confidence: moderate", "confidence: strong", 1))
    v = E.Vault(root)
    edited = v.nodes.get(f) if f else None
    check("anchor 1.4: a hand edit to strong reads back as moderate",
          edited is not None and edited["fm"].get("confidence") == "strong"
          and E.effective_confidence(edited) == "moderate")
    st = E.derive_state(v, q)
    check("anchor 1.4: ... and the question is still not settled",
          f is not None and st.get("state") != "settled")

    before = len(E.Vault(root).findings.get(h, []))
    e = _raises(E.CruxError, E.cmd_finding, root, h, "strong", direction="supports",
                why="w", exploratory=True)
    check("anchor 1.4: --exploratory on a hypothesis finding is refused with CruxError",
          e is not None)
    check("anchor 1.4: ... naming --exploratory", e is not None and "--exploratory" in str(e))
    check("anchor 1.4: ... and writes nothing", len(E.Vault(root).findings.get(h, [])) == before)


# ------------------------------------------------------------------------------- 1.4-cli
def _exploratory_cli_tests(check, tmp):
    env = _env(tmp)
    root = _vault(tmp, "v14cli")
    q, _ = E.cmd_ask(root, "What does the data show?")
    r = _cli(root, ["finding", q, "-c", "strong", "-a", "a", "--exploratory", "--json"], env)
    out = _json(r) or {}
    check("anchor 1.4-cli: finding --exploratory exits 0", r.returncode == 0)
    check("anchor 1.4-cli: ... stores moderate", out.get("stored_confidence") == "moderate")
    check("anchor 1.4-cli: ... and says it capped", out.get("capped") is True)
    r = _cli(root, ["finding", "--help"], env)
    check("anchor 1.4-cli: finding --help lists --exploratory", "--exploratory" in (r.stdout or ""))


# ------------------------------------------------------------------------------- 1.5
def _path_tests(check, tmp):
    env = _env(tmp)
    root = _vault(tmp, "v15")
    q1, _ = E.cmd_ask(root, "Top question", bears="B1")
    q2, _ = E.cmd_ask(root, "Sub question", parent=q1, bears="B2")
    h1, _, _ = E.cmd_hypothesize(root, "Anchored claim", parent=q2, expect="e", bears="B3")
    h2, _, _ = E.cmd_hypothesize(root, "Loose claim", parent=q2, expect="e")
    want = [{"id": q1, "title": "Top question", "bears_on": "B1"},
            {"id": q2, "title": "Sub question", "bears_on": "B2"},
            {"id": h1, "title": "Anchored claim", "bears_on": "B3"}]

    b = _try(E.brief, root, h1)
    check("anchor 1.5: brief (isolated) carries `path` from the top question to the item",
          b is not _ERR and b.get("path") == want)
    check("anchor 1.5: ... each entry with exactly id, title, bears_on",
          b is not _ERR and all(sorted(x) == ["bears_on", "id", "title"]
                                for x in b.get("path") or [{}]))
    b = _try(E.brief, root, h2)
    p = b.get("path") if b is not _ERR else None
    check("anchor 1.5: an item without the section has bears_on None in its path",
          bool(p) and p[-1].get("id") == h2 and p[-1].get("bears_on") is None
          and p[:-1] == want[:2])
    b = _try(E.brief, root, q2, mode="situate")
    check("anchor 1.5: brief --mode=situate carries `path` ending at its anchor",
          b is not _ERR and b.get("path") == want[:2])
    b = _try(E.brief, root, E.Vault(root).cfg["root_id"], mode="situate")
    check("anchor 1.5: situate on the project root has an empty path",
          b is not _ERR and b.get("path") == [])
    check("anchor 1.5: E.bears_path matches the brief path", _try(_bears_path, root, h1) == want)

    r = _cli(root, ["brief", h1, "--json"], env)
    check("anchor 1.5: crux brief <h> --json carries the same path",
          r.returncode == 0 and (_json(r) or {}).get("path") == want)

    f, _, _ = E.cmd_finding(root, q2, "moderate", answer="partly")
    t = _transcript(tmp, "s15", [
        ('crux hypothesize "Anchored claim" -p %s --expect e --bears B3 --json' % q2, h1),
        ('crux finding %s -c moderate -a partly --json' % q2, f)])
    r = _cli(root, ["wrap", "--json", "--transcript", t], env)
    out = _json(r) or {}
    recs = out.get("records") or []
    check("anchor 1.5: wrap --json lists both records", r.returncode == 0 and
          [x.get("id") for x in recs] == [h1, f])
    check("anchor 1.5: ... each record carries `path` equal to E.bears_path",
          len(recs) == 2 and all("path" in x for x in recs)
          and all(x.get("path") == _try(_bears_path, root, x.get("id")) for x in recs))
    check("anchor 1.5: ... the hypothesis record's path is its full path",
          len(recs) == 2 and recs[0].get("path") == want)
    check("anchor 1.5: ... a finding record's path ends at its parent",
          len(recs) == 2 and bool(recs[1].get("path"))
          and recs[1]["path"][-1].get("id") == q2)

    r = _cli(root, ["wrap", "--json", "--transcript", os.path.join(tmp, "no-such.jsonl")], env)
    out = _json(r) or {}
    check("anchor 1.5: wrap with no transcript still carries an empty review",
          r.returncode == 0 and out.get("review") == [])


# ------------------------------------------------------------------------------- 1.6
def _review_tests(check, tmp):
    env = _env(tmp)
    root = _vault(tmp, "v16")
    qs = [E.cmd_ask(root, "Question %d" % i, bears="B%d" % i)[0] for i in range(1, 6)]
    q1, q2, q3, q4, q5 = qs
    h1, _, _ = E.cmd_hypothesize(root, "Claim one", parent=q1, expect="e", bears="Bh1")
    f2, _, _ = E.cmd_finding(root, q2, "strong", answer="yes")
    q6, _ = E.cmd_ask(root, "Question six", parent=q3, bears="B6")
    h5, _, _ = E.cmd_hypothesize(root, "Claim five", parent=q5, expect="e", bears="Bh5")
    f5, _, _ = E.cmd_finding(root, h5, "strong", direction="supports", why="both bars held")
    q7, _ = E.cmd_ask(root, "Question seven", bears="B7")
    h7, _, _ = E.cmd_hypothesize(root, "Claim seven", parent=q7, expect="e", bears="Bh7")
    E.cmd_park(root, q7)
    t = _transcript(tmp, "s16", [
        ('crux hypothesize "Claim one" -p %s --expect e --bears Bh1 --json' % q1, h1),
        ('crux finding %s -c strong -a yes --json' % q2, f2),
        ('crux ask "Question six" -p %s --bears B6 --json' % q3, q6),
        ('crux hypothesize "Claim five" -p %s --expect e --bears Bh5 --json' % q5, h5),
        ('crux finding %s -c strong -d supports -w "both bars held" --json' % h5, f5),
        ('crux hypothesize "Claim seven" -p %s --expect e --bears Bh7 --json' % q7, h7)])
    r = _cli(root, ["wrap", "--json", "--transcript", t], env)
    out = _json(r) or {}
    rev = out.get("review")
    check("anchor 1.6: wrap --json carries `review`", r.returncode == 0 and isinstance(rev, list))
    rev = rev if isinstance(rev, list) else []
    check("anchor 1.6: review lists exactly the questions that gained an item and have no "
          "strong finding, in first-appearance order",
          [x.get("id") for x in rev] == [q1, q3])
    check("anchor 1.6: ... excluding a question settled by its own strong finding",
          q2 not in [x.get("id") for x in rev])
    check("anchor 1.6: ... excluding a question whose hypothesis has a strong finding",
          q5 not in [x.get("id") for x in rev])
    check("anchor 1.6: ... excluding a parked question and an untouched one",
          q7 not in [x.get("id") for x in rev] and q4 not in [x.get("id") for x in rev])
    check("anchor 1.6: each review entry has exactly id, title, path",
          bool(rev) and all(sorted(x) == ["id", "path", "title"] for x in rev))
    check("anchor 1.6: ... with path equal to E.bears_path and the question's title",
          bool(rev) and all(x.get("path") == _try(_bears_path, root, x.get("id"))
                            and x.get("title") == _node(root, x.get("id")).title for x in rev))


# ------------------------------------------------------------------------------- 1.7
TOP_KEYS = {"crux_version", "engine_version", "limits", "nodes", "project", "rd", "tasks",
            "tree", "update", "vocab", "wiki"}
PROJECT_KEYS = {"id", "status", "title", "type"}
QUESTION_KEYS = {"answer", "children", "confidence", "detail", "eli5", "findings", "id",
                 "ledger", "parent", "parked", "rd", "schema", "state", "state_finding",
                 "status", "tasks", "title", "tldr", "type", "words"}
IDEA_KEYS = {"artifacts", "confidence", "drift", "eli5", "expect", "experiments", "findings",
             "hypothesis", "id", "lock_at", "locked", "measurement", "metric", "null",
             "parent", "parked", "planned", "problem", "rd", "replicates", "rule", "rule_m",
             "run_links", "schema", "state", "state_finding", "status", "tally", "tasks",
             "title", "tldr", "type", "verifiables", "words"}
FINDING_KEYS = {"answer", "confidence", "created", "direction", "effective_confidence",
                "evidence", "id", "null", "parent", "verifiables", "vs_expect", "why"}


def _status_tests(check, tmp):
    env = _env(tmp)
    copy = os.path.join(tmp, "demo17")
    shutil.copytree(DEMO, copy)
    r = _cli(copy, ["status", "--json"], env)
    d = _json(r) or {}
    nodes = d.get("nodes") or {}
    by = lambda t: [n for n in nodes.values() if n.get("type") == t]
    check("anchor 1.7: status --json top-level keys unchanged",
          r.returncode == 0 and set(d) == TOP_KEYS)
    check("anchor 1.7: ... project node keys unchanged",
          bool(by("project")) and all(set(n) == PROJECT_KEYS for n in by("project")))
    check("anchor 1.7: ... question node keys unchanged",
          bool(by("question")) and all(set(n) == QUESTION_KEYS for n in by("question")))
    check("anchor 1.7: ... hypothesis node keys unchanged",
          bool(by("idea")) and all(set(n) == IDEA_KEYS for n in by("idea")))
    fs = [f for n in nodes.values() for f in (n.get("findings") or [])]
    check("anchor 1.7: ... finding keys unchanged",
          bool(fs) and all(set(f) == FINDING_KEYS for f in fs))

    root = _vault(tmp, "v17")
    q, _ = E.cmd_ask(root, "What does the data show?")
    r0 = _try(E.cmd_finding, root, q, "strong", answer="a", exploratory=True)
    r = _cli(root, ["status", "--json"], env)
    fs = [f for n in ((_json(r) or {}).get("nodes") or {}).values()
          for f in (n.get("findings") or [])]
    check("anchor 1.7: an exploratory finding adds no key to its finding JSON",
          r0 is not _ERR and len(fs) == 1 and set(fs[0]) == FINDING_KEYS)


# ------------------------------------------------------------------------------- ix
def _tree_bytes(root):
    out = {}
    for d, dirs, files in os.walk(root):
        for fn in files:
            p = os.path.join(d, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


def _states(root):
    return {k: (n.get("state"), n.get("confidence"))
            for k, n in E.snapshot(root)["nodes"].items()}


def _version_tests(check, tmp):
    import migrate4
    check("anchor ix: ENGINE_VERSION is 4.1", E.ENGINE_VERSION == "4.1")
    check("anchor ix: migrate4.TARGET stays 4.0", migrate4.TARGET == "4.0")
    check("anchor ix: a 4.0 vault needs no migration", migrate4.needs_migration("4.0") is False)

    examples = os.path.dirname(DEMO)
    vaults = sorted(d for d in os.listdir(examples)
                    if d.endswith("_vault") and os.path.isdir(os.path.join(examples, d)))
    check("anchor ix: the committed example vaults are found", len(vaults) >= 4)
    for name in vaults:
        try:
            _version_one(check, tmp, os.path.join(examples, name), name)
        except Exception as e:
            check("anchor ix: %s crashed: %s: %s" % (name, type(e).__name__, e), False)


def _stamp(marker):
    return str(E.yaml_load(_read(marker)).get("engine_version"))


def _version_one(check, tmp, src, name):
    """Decision ix: a copy of a committed example vault loads at 4.1 with no file rewritten
    beyond the version stamp and no node's state or confidence moved. Only a copy stamped
    4.0 before the load gets the drift line and the one-line .crux.yaml diff; a copy already
    stamped 4.1 loads with nothing changed at all."""
    copy = os.path.join(tmp, "ix_" + name)
    shutil.copytree(src, copy)
    marker = os.path.join(copy, E.VAULT_MARKER)
    was = _stamp(marker)
    check("anchor ix: %s is stamped 4.0 or 4.1 before the load" % name, was in ("4.0", "4.1"))
    before, states = _tree_bytes(copy), _states(copy)
    had_dot_crux = os.path.isdir(os.path.join(copy, ".crux"))
    msg = _try(E.check_and_stamp_version, copy)
    after = _tree_bytes(copy)
    check("anchor ix: %s reads 4.1 after the load" % name, _stamp(marker) == "4.1")
    check("anchor ix: %s gains no `.crux/` directory, no backup and no new file" % name,
          set(after) == set(before)
          and os.path.isdir(os.path.join(copy, ".crux")) == had_dot_crux)
    check("anchor ix: %s keeps every file but .crux.yaml byte-identical" % name,
          all(after.get(k) == b for k, b in before.items() if k != E.VAULT_MARKER))
    check("anchor ix: %s moves no node's state or confidence" % name, _states(copy) == states)
    if was == "4.0":
        check("anchor ix: %s (stamped 4.0) returns the drift line, not a migration line" % name,
              isinstance(msg, str) and msg.startswith("engine drift:") and "v4.0" in msg
              and "migrat" not in msg.lower())
        b = before.get(E.VAULT_MARKER, b"").decode().splitlines()
        a = after.get(E.VAULT_MARKER, b"").decode().splitlines()
        diff = [(x, y) for x, y in zip(b, a) if x != y]
        check("anchor ix: %s (stamped 4.0) .crux.yaml differs only on the engine_version line"
              % name, len(a) == len(b) and len(diff) == 1
              and diff[0][0].startswith("engine_version:")
              and diff[0][1].startswith("engine_version:"))
    else:
        check("anchor ix: %s (stamped 4.1) loads with no drift line and an unchanged "
              ".crux.yaml" % name,
              msg is None and after.get(E.VAULT_MARKER) == before.get(E.VAULT_MARKER))


# ------------------------------------------------------------------------------- driver
def run_all(check):
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="crux_anchor_"))
    try:
        for prefix, section in (("1.1", _cli_bears_tests), ("1.2", _api_tests),
                                ("1.3", _validate_tests), ("1.4", _exploratory_tests),
                                ("1.4-cli", _exploratory_cli_tests), ("1.5", _path_tests),
                                ("1.6", _review_tests), ("1.7", _status_tests),
                                ("ix", _version_tests)):
            try:
                section(check, tmp)
            except Exception as e:      # an unexpected result is a FAIL line, never a traceback
                check("anchor %s: %s crashed: %s: %s"
                      % (prefix, section.__name__, type(e).__name__, e), False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)
        print(("  ok   " if cond else "  FAIL ") + name)
    run_all(check)
    print(f"\n  PASSED {len(passed)} / {len(passed) + len(failed)}")
    if failed:
        print("  FAILED:\n" + "\n".join("    " + f for f in failed))
        sys.exit(1)
    print("  ALL GREEN")


if __name__ == "__main__":
    main()
