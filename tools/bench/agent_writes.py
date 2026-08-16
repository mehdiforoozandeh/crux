#!/usr/bin/env python3
"""Simulate an agent writing to a crux vault at ~1 Hz, for the spec-12 criterion
"an idle cockpit with a vault under active agent writes holds under 5% of a core
across client and server combined" (tools/bench/).

Usage:
    python3 tools/bench/agent_writes.py VAULT_DIR [--mode prose|vstate] [--seconds 60]

Modes (both edit ONE hypothesis file, chosen deterministically):
    prose  (default) — rewrites the Findings paragraph with a counter word each
           tick. Drawn tree unchanged: post-P3 this exercises the tier-1 skip.
    vstate — toggles the first verifiable checkbox each tick. Changes a drawn
           badge (and any derived verdict color): exercises the tier-2 patch.

VAULT_DIR must be a scratch COPY — this tool mutates files in place. Measure
while it runs: server CPU via `ps -o %cpu -p <serve pid>`, client via the
probe's Part A / a browser task manager. Ctrl-C to stop; the file is restored.
"""
import argparse
import os
import re
import sys
import time


def pick_target(vault):
    for name in sorted(os.listdir(vault)):
        if re.match(r"h\d+_.*\.md$", name):
            return os.path.join(vault, name)
    print("no hypothesis file (h*_*.md) found in", vault)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--mode", choices=("prose", "vstate"), default="prose")
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    vault = os.path.abspath(args.vault)
    target = pick_target(vault)
    original = open(target, encoding="utf-8").read()
    print(f"editing {os.path.basename(target)} at 1 Hz for {args.seconds}s (mode={args.mode})")
    try:
        for tick in range(args.seconds):
            text = original
            if args.mode == "prose":
                # rewrite the Findings body (prose only — no drawn field changes)
                text = re.sub(r"(## Findings\n\n)(.*?)(\n*$)",
                              rf"\g<1>bench tick {tick}: findings prose rewritten.\n",
                              text, flags=re.S)
            else:
                # flip the first verifiable checkbox (a drawn badge changes state)
                box = "- [ ]" if tick % 2 == 0 else "- [x]"
                text = re.sub(r"- \[[ x]\]", box, text, count=1)
            with open(target, "w", encoding="utf-8") as f:
                f.write(text)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        with open(target, "w", encoding="utf-8") as f:
            f.write(original)
        print("restored", os.path.basename(target))


if __name__ == "__main__":
    main()
