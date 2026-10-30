#!/usr/bin/env bash
# Build the frozen work dir: the M4 Weekly data and four published Weekly forecasts from the
# official M4-methods repository (pinned commit, every file pinned by sha256), and an isolated
# venv for candidate programs. Nothing is installed globally. Idempotent; safe to re-run.
# On an Alliance cluster (Fir), first run:  module load python/3.11.5
# and the venv is built from the cluster's own wheelhouse (pip --no-index).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
SECRET="$WORK/secret"          # hidden from every candidate run (score.py mounts over it)
PIN=6c1067e5a57161249b17289a565178dc7a3fb3ca  # Mcompetitions/M4-methods master, 2020-03-20
BASE="https://raw.githubusercontent.com/Mcompetitions/M4-methods/$PIN"
PY="${PYTHON:-python3}"

# path in the repo (URL-encoded) | local name | sha256
FILES="
Dataset/Train/Weekly-train.csv|Weekly-train.csv|d478d3f6ed673e6ed3c2cb0fbed5425f72eedd51318ebebeb0b5ecfcefc37714
Dataset/Test/Weekly-test.csv|Weekly-test.csv|3b2bc4be8e636e802260dcd843ca3c5da40536a1fbe1ecb3229a97dae4f44688
Dataset/M4-info.csv|M4-info.csv|26a75cc9b9f65e351b39b0bdbb7e3464ac837df0baf541ab55abdd2ba1a14c88
Evaluation%20and%20Ranks.xlsx|Evaluation_and_Ranks.xlsx|9da8ca21011d747daa1de43d4157ed19ad85a089de9ba3a7da39ead78a49d51e
Point%20Forecasts/submission-Naive2.rar|submission-Naive2.rar|beb03737f329449cee17627cf31eed9637416a35b656568702c6fdb6ab607895
Point%20Forecasts/submission-Theta.rar|submission-Theta.rar|57326ea8ab8e3cb98c4267cd5750c128e48b16fff0e53bcb8a11abacf22c5d12
Point%20Forecasts/submission-118.rar|submission-118.rar|6c0f887e1f319f1b089eab9935ba5fa780ef90a214b8eda09584ac50e8ffcee7
Point%20Forecasts/submission-235.rar|submission-235.rar|0a73dabe5f3c8e9b115c3682934be36fea6adb3e1f31afd8e8c38a9a26e5a1ff
"

if command -v sha256sum >/dev/null; then SHA="sha256sum"; else SHA="shasum -a 256"; fi
mkdir -p "$SECRET/raw" "$SECRET/published"
echo "$FILES" | while IFS='|' read -r src name want; do
  [ -n "$src" ] || continue
  dst="$SECRET/raw/$name"
  if [ ! -f "$dst" ]; then
    curl -sSfL -o "$dst.part" "$BASE/$src" && mv "$dst.part" "$dst"
  fi
  got="$($SHA "$dst" | cut -d' ' -f1)"
  if [ "$got" != "$want" ]; then
    echo "$name sha256 mismatch: got $got, want $want" >&2; exit 1
  fi
done
cp "$SECRET/raw/Weekly-train.csv" "$SECRET/raw/Weekly-test.csv" "$SECRET/"

# The published point forecasts: keep the 359 Weekly rows, first 13 columns. bsdtar
# (libarchive) reads these RAR files; Fir's 7z lacks the RAR codec.
for name in Naive2 Theta 118 235; do
  out="$SECRET/published/$name.csv"
  [ -f "$out" ] && continue
  tmp="$(mktemp -d "$WORK/rar.XXXXXX")"
  (cd "$tmp" && bsdtar -xf "$SECRET/raw/submission-$name.rar")
  csv="$(ls "$tmp"/*.csv)"
  { head -1 "$csv" | cut -d, -f1-14; grep -E '^"?W[0-9]+"?,' "$csv" | cut -d, -f1-14; } > "$out.part"
  mv "$out.part" "$out"; rm -rf "$tmp"
  test "$(wc -l < "$out")" -eq 360
done

# The venv candidate programs run in. Scientific stack only: statistical (statsmodels),
# tree and neural (scikit-learn) families. The parent scorer itself is stdlib-only.
if [ ! -x "$WORK/venv/bin/python" ]; then
  "$PY" -m venv "$WORK/venv"
fi
PIP=("$WORK/venv/bin/python" -m pip install --quiet)
if [ -d /cvmfs/soft.computecanada.ca ]; then
  PIP+=(--no-index)                     # Alliance: the cluster's own wheelhouse only
else
  "$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
  PIP+=(--only-binary=:all:)
fi
"${PIP[@]}" -r "$HERE/requirements.lock"
{ "$WORK/venv/bin/python" --version; "$WORK/venv/bin/python" -m pip freeze; } > "$WORK/versions.txt"
echo "ready: $WORK  (versions in work/versions.txt)"
