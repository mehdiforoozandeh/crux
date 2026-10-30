#!/usr/bin/env python3
"""Validation suite for score.py: builds candidate programs in work/cases/ and checks that
the scorer passes the honest ones and refuses every cheat. Prints one JSON report.

    work/venv/bin/python validate.py [--repeats K]

Run after setup.sh, on a machine with internet. AlphaEvolve's construction is fetched into
memory (sha256-pinned) and never stored under this directory; the case programs live in a
temp directory outside it, deleted at the end. Each case also records what OpenEvolve's circle_packing evaluator logic
(validate_packing as of issue #183, before the centre-NaN check of PR #184) would have said,
reimplemented below, to show which holes this scorer closes.
"""
import hashlib, json, math, os, shutil, subprocess, sys, tempfile, textwrap, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
AE_URL = ("https://raw.githubusercontent.com/google-deepmind/alphaevolve_repository_of_problems/"
          "30f8c3ecda318e3ac31ff2c3290884316ac7d0ed/experiments/packing_circles_max_sum_of_radii/"
          "packing_circles_max_sum_of_radii.ipynb")
AE_SHA = "e7a304378a5ca80c74f94f5060a9f5db953767af850834513fd797e3306a935e"


def fetch_ae():
    raw = urllib.request.urlopen(AE_URL, timeout=30).read()
    if hashlib.sha256(raw).hexdigest() != AE_SHA:
        raise SystemExit("AlphaEvolve notebook sha256 mismatch")
    import numpy as np
    nb = json.loads(raw)
    src = next("".join(c["source"]) for c in nb["cells"]
               if "centers_26 = np.array" in "".join(c["source"]))
    g = {"np": np}
    exec(src, g)
    return {"centers": g["centers_26"].tolist(), "radii": g["radii_26"].tolist()}


AE = fetch_ae()
CASES = tempfile.mkdtemp(prefix="circpack-cases-")
SCORER = os.path.join(HERE, "score.py")

GRID = [[x, y, 0.1] for x in (0.1, 0.3, 0.5, 0.7, 0.9) for y in (0.1, 0.3, 0.5, 0.7, 0.9)]
GAP = [0.2, 0.2, 0.1 * (math.sqrt(2.0) - 1.0) - 1e-12]
BASE = GRID + [GAP]


def ae(shrink=0.0, grow=0.0):
    return [[x, y, r - shrink + grow] for (x, y), r in zip(AE["centers"], AE["radii"])]


def prints(obj):
    """A program that prints this exact text (json.dumps keeps NaN / Infinity as such)."""
    return f"import sys\nsys.stdout.write({json.dumps(obj, allow_nan=True)!r})\n"


def mod(circles, i, k, v):
    c = [list(t) for t in circles]
    c[i][k] = v
    return c


NAN_183 = [[float("nan"), float("nan"), 4.01445 / 26] for _ in range(26)]   # the reported 4.0145
NAN_285 = [[float("nan"), float("nan"), 0.1] for _ in range(25)] + [[float("nan"), float("nan"), 2.637 - 2.5]]
NET = textwrap.dedent(f"""
    import json, urllib.request
    url = {AE_URL!r}
    nb = json.load(urllib.request.urlopen(url, timeout=20))
    import numpy as np
    src = next("".join(c["source"]) for c in nb["cells"] if "centers_26 = np.array" in "".join(c["source"]))
    g = {{"np": np}}; exec(src, g)
    out = [[float(x), float(y), float(r) - 1e-12] for (x, y), r in zip(g["centers_26"], g["radii_26"])]
    print(json.dumps({{"circles": out}}))
""")

# Looks for the reference material where setup.sh used to keep it, then for AlphaEvolve's first
# coordinate anywhere under the scorer's directory (the venv aside). Found -> prints the record
# (a leak passes, near 2.636); not found -> crashes (the expected outcome).
LEAK = textwrap.dedent(f"""
    import json, os, sys
    here = {HERE!r}
    old = os.path.join(here, "work", "reference", "alphaevolve_26.json")
    if os.path.exists(old):
        ae = json.load(open(old))
        print(json.dumps({{"circles": [[x, y, r - 1e-12] for (x, y), r in zip(ae["centers"], ae["radii"])]}}))
        sys.exit(0)
    marker = b"0.70260960" + b"36990247"     # split, so this text itself never matches
    for root, dirs, files in os.walk(here):
        dirs[:] = [d for d in dirs if d != "venv"]
        for f in files:
            p = os.path.join(root, f)
            try:
                if os.path.getsize(p) < 5 << 20 and marker in open(p, "rb").read():
                    sys.stderr.write("LEAK: " + p)
                    print(json.dumps({{"circles": {BASE!r}}}))
                    sys.exit(0)
            except OSError:
                pass
    raise SystemExit("no reference material readable under " + here)
""")

# name -> (program source, expected: "pass" | "fail" | "pass-or-fail", OpenEvolve-check input)
CASES_SPEC = {
    "baseline": (open(os.path.join(HERE, "baseline", "pack.py")).read(), "pass", BASE),
    "alphaevolve_shrunk_1e-12": (prints({"circles": ae(shrink=1e-12)}), "pass", ae(shrink=1e-12)),
    "alphaevolve_as_published": (prints({"circles": ae()}), "fail", ae()),
    "nan_centre": (prints({"circles": mod(BASE, 3, 0, float("nan"))}), "fail", mod(BASE, 3, 0, float("nan"))),
    "nan_centres_sum_4.01_issue183": (prints({"circles": NAN_183}), "fail", NAN_183),
    "nan_centres_hardcoded_radii_issue285": (prints({"circles": NAN_285}), "fail", NAN_285),
    "tolerance_exploit_issue183_r+5e-7": (prints({"circles": ae(grow=5e-7)}), "fail", ae(grow=5e-7)),
    "string_nan": ("print('{\"circles\": ' + str([['nan', 0.5, 0.1]] * 26).replace(\"'\", '\"') + '}')\n", "fail", None),
    "infinite_radius": (prints({"circles": mod(BASE, 0, 2, float("inf"))}), "fail", mod(BASE, 0, 2, float("inf"))),
    "overlap_by_1e-15": (prints({"circles": mod(BASE, 6, 2, 0.1 + 1e-15)}), "fail", mod(BASE, 6, 2, 0.1 + 1e-15)),
    "outside_by_1e-13": (prints({"circles": mod(BASE, 0, 0, 0.1 - 1e-13)}), "fail", mod(BASE, 0, 0, 0.1 - 1e-13)),
    "zero_radius": (prints({"circles": mod(BASE, 25, 2, 0.0)}), "fail", mod(BASE, 25, 2, 0.0)),
    "negative_radius": (prints({"circles": mod(BASE, 25, 2, -0.01)}), "fail", mod(BASE, 25, 2, -0.01)),
    "n25": (prints({"circles": BASE[:25]}), "fail", BASE[:25]),
    "n27": (prints({"circles": BASE + [[0.4, 0.4, 0.01]]}), "fail", BASE + [[0.4, 0.4, 0.01]]),
    "fake_score_key": (prints({"circles": BASE, "sum_radii": 4.01}), "fail", None),
    "fake_score_line": ("print('sum_radii: 4.01')\n" + prints({"circles": BASE}), "fail", None),
    "two_json_objects": (prints({"circles": BASE}) + prints({"circles": ae()}), "fail", None),
    "bool_value": (prints({"circles": mod(BASE, 0, 2, True)}), "fail", None),
    "huge_exponent": ("print('{\"circles\": [' + ','.join(['[0.5, 0.5, 1e-99999999]'] * 26) + ']}')\n", "fail", None),
    "timeout_sleep_120s": ("import time\ntime.sleep(120)\n", "fail", None),
    "fork_child_lingers": ("import os, sys, time\nif os.fork() == 0:\n    time.sleep(300)\n    os._exit(0)\n"
                           + prints({"circles": BASE}), "pass", None),
    "memory_hog_8GB": ("import numpy as np\na = np.ones(1 << 30)\n", "fail", None),
    "stdout_flood_10MB": ("import sys\nsys.stdout.write('x' * (10 << 20))\n", "fail", None),
    "crash": ("raise SystemExit(3)\n", "fail", None),
    "network_fetch_record": (NET, "fail-if-blocked", None),
    "read_reference_from_disk": (LEAK, "fail", None),
}


def openevolve_valid(circles):
    """OpenEvolve examples/circle_packing validate_packing + shape check, as it stood when
    issue #183 was filed: no centre-NaN check, 1e-6 tolerance on walls and pairs."""
    if circles is None:
        return None
    import numpy as np
    c = np.array([[t[0], t[1]] for t in circles], float); r = np.array([t[2] for t in circles], float)
    if c.shape != (26, 2) or r.shape != (26,):
        return False
    for i in range(26):
        if r[i] < 0 or np.isnan(r[i]):
            return False
        x, y = c[i]
        if x - r[i] < -1e-6 or x + r[i] > 1 + 1e-6 or y - r[i] < -1e-6 or y + r[i] > 1 + 1e-6:
            return False
    for i in range(26):
        for j in range(i + 1, 26):
            if np.sqrt(np.sum((c[i] - c[j]) ** 2)) < r[i] + r[j] - 1e-6:
                return False
    return True


def score(path):
    t = time.monotonic()
    p = subprocess.run([sys.executable, SCORER, path], capture_output=True, text=True)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"unparseable": p.stdout[:200]}
    return p.returncode, out, round(time.monotonic() - t, 2)


def main():
    try:
        run()
    finally:
        shutil.rmtree(CASES, ignore_errors=True)


def run():
    repeats = int(sys.argv[sys.argv.index("--repeats") + 1]) if "--repeats" in sys.argv else 3
    report, ok = {}, True
    for name, (src, want, oe_in) in CASES_SPEC.items():
        d = os.path.join(CASES, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "pack.py"), "w") as f:
            f.write(src)
        rc, out, wall = score(d)
        got = "pass" if rc == 0 and out.get("passed") is True and "sum_radii" in out else "fail"
        net = out.get("sandbox", {}).get("network")
        if want == "fail-if-blocked":
            good = got == "fail" if rc != 0 or "blocked" in str(net) else True
        else:
            good = got == want
        ok &= good
        oe = openevolve_valid(oe_in)
        report[name] = {"expected": want, "got": got, "ok": good, "exit": rc, "wall_s": wall,
                        "sum_radii": out.get("sum_radii", {}).get("value"),
                        "suspicious": out.get("suspicious"),
                        "reason": out.get("reason"), "openevolve_would_accept": oe}
    det = {}
    for name in ("baseline", "alphaevolve_shrunk_1e-12"):
        vals = [score(os.path.join(CASES, name))[1].get("sum_radii", {}).get("exact")
                for _ in range(repeats)]
        det[name] = {"runs": repeats, "identical": len(set(vals)) == 1, "exact": vals[0]}
        ok &= det[name]["identical"]
    print(json.dumps({"all_ok": ok, "cases": report, "determinism": det}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
