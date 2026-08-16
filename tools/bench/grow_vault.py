#!/usr/bin/env python3
"""Grow a scratch crux vault with synthetic nodes, through the real CLI, so every
node is format-valid (spec 12 bench harness — tools/bench/).

Usage:
    python3 tools/bench/grow_vault.py VAULT_DIR [N_QUESTIONS] [H_PER_QUESTION]

VAULT_DIR must be an existing crux vault you are happy to mutate — ALWAYS a copy
(e.g. of skills/crux/examples/demo_vault), never a real research vault. Seeded,
so the same arguments grow the same tree.
"""
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CRUX = os.path.join(HERE, "..", "..", "skills", "crux", "scaffold", "crux.py")


def crux(vault, *args):
    r = subprocess.run([sys.executable, CRUX, *args], cwd=vault,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL:", args, (r.stderr or r.stdout)[-400:])
        sys.exit(1)
    return r.stdout


WORDS = ("latent representation transfer frozen decoder probe augmentation "
         "schedule batch norm contrastive masking ratio resolution token "
         "distillation objective sampling curriculum floor ceiling budget").split()


def title(kind, i, rng):
    return f"Synthetic {kind} {i}: " + " ".join(rng.sample(WORDS, rng.randint(3, 8)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    vault = os.path.abspath(sys.argv[1])
    n_q = int(sys.argv[2]) if len(sys.argv) > 2 else 28
    h_per_q = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    if not os.path.isdir(vault):
        print(f"no such vault dir: {vault}")
        sys.exit(2)
    rng = random.Random(11)

    # existing questions to hang new subtrees off (text status is the stable parse)
    txt = crux(vault, "status")
    qids = sorted(set(re.findall(r"\b(q\d+)\b", txt)))
    print("existing questions:", qids or "(none)")

    new_qs = []
    for i in range(n_q):
        parent = rng.choice(qids + new_qs) if (qids or new_qs) else None
        args = ["ask", "--json", title("question", i, rng)]
        if parent and rng.random() < 0.8:
            args += ["-p", parent]
        out = json.loads(crux(vault, *args))
        qid = out.get("id") or out.get("node", {}).get("id")
        new_qs.append(qid)
        for j in range(h_per_q):
            crux(vault, "hypothesize", "--json", title("hypothesis", f"{i}.{j}", rng),
                 "-p", qid, "-v", f"synthetic metric {j} >= {rng.randint(1, 9) / 10}")
        print(f"{qid}: +{h_per_q} hypotheses")
    print(f"done: +{n_q} questions, +{n_q * h_per_q} hypotheses in {vault}")


if __name__ == "__main__":
    main()
