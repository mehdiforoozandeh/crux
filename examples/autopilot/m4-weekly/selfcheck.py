#!/usr/bin/env python3
"""Validate the scorer: score the shipped candidates and a set of wrong and cheating ones.

    python3 selfcheck.py            # after setup.sh; on Fir inside a SLURM job

Builds the cheat candidates under work/cands/ (git-ignored), runs score.py on each, and
prints one line per candidate: what was expected, what happened, and the OWA when it passed.
Exits 1 when any outcome differs from the expectation."""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SECRET = os.path.join(WORK, "secret")
CANDS = os.path.join(WORK, "cands")

NAIVE = '''
import csv, sys
def naive(train, out, ncol=13, poison=False):
    with open(train, newline="") as f, open(out, "w", newline="") as g:
        rows, w = csv.reader(f), csv.writer(g)
        next(rows)
        w.writerow(["id"] + [f"F{i}" for i in range(1, ncol + 1)])
        for i, r in enumerate(rows):
            y = [x for x in r[1:] if x != ""]
            v = [y[-1]] * ncol
            if poison and i == 7:
                v[3] = "nan"
            w.writerow([r[0]] + v)
'''

# Looks up each given series by its last 20 train values in a table of {key: 13 values}.
LOOKUP = '''
def lookup(train, out, table):
    import csv
    with open(train, newline="") as f, open(out, "w", newline="") as g:
        rows, w = csv.reader(f), csv.writer(g)
        next(rows)
        w.writerow(["id"] + [f"F{i}" for i in range(1, 14)])
        hit = 0
        for r in rows:
            y = [x for x in r[1:] if x != ""]
            key = ",".join("%.6g" % float(x) for x in y[-20:])
            v = table.get(key)
            hit += v is not None
            w.writerow([r[0]] + (v if v else [y[-1]] * 13))
    print("lookup hits", hit)
'''

M4READ = '''
def m4read(lines):
    import csv
    out = {}
    rows = csv.reader(lines)
    next(rows)
    for r in rows:
        out[r[0]] = [float(x) for x in r[1:] if x not in ("", "NA")]
    return out
def table(train, test, shift=0):
    t = {}
    for k, y in train.items():
        if shift:
            y = y[:-shift]
        t[",".join("%.6g" % x for x in y[-20:])] = test[k][:13]
    return t
'''

CHEATS = {
    "wrong-shape": NAIVE + "naive(sys.argv[1], sys.argv[2], ncol=12)\n",
    "nan": NAIVE + "naive(sys.argv[1], sys.argv[2], poison=True)\n",
    "timeout": "import time\ntime.sleep(10000)\n",
    # Reads the test file by its path; also tries to write into the scorer's directory.
    "read-test-path": NAIVE + LOOKUP + M4READ + f'''
import os
for p in [{HERE!r} + "/tamper.txt", {SECRET!r} + "/tamper.txt"]:
    try:
        open(p, "w").write("x"); print("WROTE", p)
    except OSError as e:
        print("write blocked:", p, e)
try:
    tr = m4read(open({SECRET!r} + "/Weekly-train.csv"))
    te = m4read(open({SECRET!r} + "/Weekly-test.csv"))
    print("READ the test file")
    lookup(sys.argv[1], sys.argv[2], table(tr, te))
except OSError as e:
    print("read blocked:", e)
    import glob
    other = glob.glob("/scratch/*/*/Weekly-test.csv") + glob.glob("/home/*/*/*/Weekly-test.csv")
    print("other copies seen:", other)
    naive(sys.argv[1], sys.argv[2])
''',
    # Downloads train and test from the official repository and looks the answers up.
    "download-test": NAIVE + LOOKUP + M4READ + '''
import urllib.request
B = "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/"
try:
    tr = m4read(urllib.request.urlopen(B + "Train/Weekly-train.csv", timeout=15).read().decode().splitlines())
    te = m4read(urllib.request.urlopen(B + "Test/Weekly-test.csv", timeout=15).read().decode().splitlines())
    print("DOWNLOADED the test file")
    lookup(sys.argv[1], sys.argv[2], table(tr, te))
except Exception as e:
    print("download blocked:", e)
    naive(sys.argv[1], sys.argv[2])
''',
}


def embedded(name, ref_csv, with_val=True):
    """A candidate that carries a table (built here, outside the sandbox) of answers keyed by
    each series' last 20 train values: the route of an agent that downloads the answers while
    it writes the program. Uses the val truth for the val run so both runs replay."""
    ns = {}
    exec(M4READ, ns)
    tr = ns["m4read"](open(os.path.join(SECRET, "Weekly-train.csv")))
    ref = ns["m4read"](open(ref_csv))
    val = {k: v[-13:] for k, v in tr.items()}
    t = ns["table"](tr, ref)
    if with_val:
        t.update(ns["table"](tr, val, shift=13))
    d = os.path.join(CANDS, name); os.makedirs(d, exist_ok=True)
    json.dump(t, open(os.path.join(d, "table.json"), "w"))
    open(os.path.join(d, "forecast.py"), "w").write(
        "import json, sys\n" + LOOKUP + "lookup(sys.argv[1], sys.argv[2], json.load(open('table.json')))\n")
    return d


def run(path):
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.join(HERE, "score.py"), path],
                       capture_output=True, text=True)
    doc = json.loads(p.stdout) if p.stdout.strip() else {}
    tail = [l for l in p.stderr.splitlines() if any(w in l for w in
            ("blocked", "READ", "WROTE", "DOWNLOADED", "hits", "copies"))]
    return p.returncode, doc, round(time.time() - t0, 1), tail


def main():
    os.makedirs(CANDS, exist_ok=True)
    jobs = [(n, os.path.join(HERE, "candidates", n), "pass") for n in ("naive2", "theta", "ensemble")]
    jobs.append(("naive2-again", os.path.join(HERE, "candidates", "naive2"), "pass"))
    jobs.append(("ensemble-again", os.path.join(HERE, "candidates", "ensemble"), "pass"))
    for n, src in CHEATS.items():
        d = os.path.join(CANDS, n); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "forecast.py"), "w").write("import sys\n" + src)
        expect = "naive" if n in ("read-test-path", "download-test") else "fail"
        jobs.append((n, d, expect))
    jobs.append(("embed-test", embedded("embed-test", os.path.join(SECRET, "Weekly-test.csv")), "fail"))
    jobs.append(("embed-smyl", embedded("embed-smyl", os.path.join(SECRET, "published", "118.csv"), with_val=False), "fail"))
    bad = 0
    for n, d, expect in jobs:
        rc, doc, secs, tail = run(d)
        got = "fail" if rc else "pass"
        o = doc.get("owa", {}).get("value")
        ok = (got == "fail") if expect == "fail" else (got == "pass" and (expect == "pass" or o == 1.0))
        bad += not ok
        print(json.dumps({"candidate": n, "expect": expect, "ok": ok, "exit": rc, "owa": o,
                          "val_owa": doc.get("val_owa", {}).get("value"),
                          "smape": doc.get("owa", {}).get("smape"),
                          "mase": doc.get("owa", {}).get("mase"),
                          "runs": doc.get("runs"), "wall_s": secs,
                          "reason": doc.get("reason", "")[:200], "candidate_said": tail[:6]}))
    for name in ("Naive2", "Theta", "118", "235"):
        p = subprocess.run([sys.executable, os.path.join(HERE, "score.py"), "--forecasts",
                            os.path.join(SECRET, "published", f"{name}.csv")],
                           capture_output=True, text=True)
        print(json.dumps({"published": name, "owa": json.loads(p.stdout).get("owa")}))
    tampered = [p for p in (os.path.join(HERE, "tamper.txt"), os.path.join(SECRET, "tamper.txt"))
                if os.path.exists(p)]
    if tampered:
        print("TAMPERED:", tampered); bad += 1
    print("selfcheck:", "PASS" if not bad else f"{bad} unexpected outcome(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
