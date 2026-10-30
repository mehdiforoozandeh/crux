#!/bin/bash
# Run one autopilot benchmark on Fir inside a single SLURM job.
#   bash examples/autopilot/run-fir.sh [--dry-run] <memesuite-lite|nanogpt-shakespeare|circle-packing|m4-weekly>
# On the login node it submits itself with the benchmark's resources and prints the job id.
# Inside the job (--job) it builds ~/scratch/crux-runs/<bench>-<jobid>/{repo,vault} and runs
# `crux auto run`. --dry-run prints the sbatch line and the substituted plan, and touches nothing.
# The worker uses the Fir `claude` CLI's own login; this script reads no credential.
set -euo pipefail
MODE=submit
case "${1:-}" in --dry-run) MODE=dry; shift ;; --job) MODE=job; shift ;; esac
B="${1:?usage: run-fir.sh [--dry-run] <benchmark>}"
CRUX=~/scratch/crux
BENCH="$CRUX/examples/autopilot/$B"
RUNS=~/scratch/crux-runs
PY=python/3.11.5
case "$B" in
  memesuite-lite)      SRC=work/cand-baseline;  RES=(--account=def-maxwl_cpu --cpus-per-task=8 --mem=16000M) ;;
  nanogpt-shakespeare) SRC=work/cand-baseline;  PY="StdEnv/2023 python/3.12.4"
                       RES=(--account=def-maxwl_gpu --gpus=h100:1 --cpus-per-task=4 --mem=32000M) ;;
  circle-packing)      SRC=baseline;            RES=(--account=def-maxwl_cpu --cpus-per-task=4 --mem=8000M) ;;
  m4-weekly)           SRC=candidates/naive2;   RES=(--account=def-maxwl_cpu --cpus-per-task=4 --mem=16000M) ;;
  *) echo "run-fir.sh: unknown benchmark '$B'" >&2; exit 2 ;;
esac
# Inside the job, $0 is SLURM's spooled copy, so the plan comes from the Fir checkout.
PLAN_SRC="$(cd "$(dirname "$0")" && pwd)/$B/plan.md"
[ "$MODE" = job ] && PLAN_SRC="$BENCH/plan.md"
HOURS=$(sed -n 's/^budget_hours: *//p' "$PLAN_SRC")
TIME="$(( ${HOURS%.*} + 1 )):00:00"
SBATCH=(sbatch --parsable --job-name="crux-$B" --time="$TIME" "${RES[@]}"
        --output="$RUNS/slurm_logs/%x-%j.out" "$CRUX/examples/autopilot/run-fir.sh" --job "$B")
subst() { sed -e "s|@BENCH@|$BENCH|g" -e "s|@ANCHOR@|$1|g" -e "s|@REPO@|$2|g" "$PLAN_SRC"; }

if [ "$MODE" = dry ]; then
  echo "${SBATCH[*]}"
  echo "# job: module load $PY; R=$RUNS/$B-<jobid>; copy $BENCH/$SRC to R/repo (git, one commit);"
  echo "#      crux init R/vault; crux ask; crux auto check --static; crux auto run R/vault/auto/q1/plan.md"
  subst q1 "$RUNS/$B-<jobid>/repo"
  exit 0
fi
if [ "$MODE" = submit ]; then
  mkdir -p "$RUNS/slurm_logs"
  "${SBATCH[@]}"
  exit 0
fi

# ---- inside the job
module load $PY
export PATH="$HOME/.local/bin:$PATH"
R="$RUNS/$B-$SLURM_JOB_ID"
mkdir -p "$R/repo"
cp -a "$BENCH/$SRC/." "$R/repo/"
rm -rf "$R/repo/.git"
git -C "$R/repo" init -q
git -C "$R/repo" add -A
git -C "$R/repo" commit -qm "base: $B $SRC"
"$CRUX/crux" init "$B" --dir "$R/vault" --goal "Improve the $B benchmark score."
cd "$R/vault"
Q=$("$CRUX/crux" ask "Can an autopilot search beat the $B baseline?" --json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
mkdir -p "auto/$Q"
subst "$Q" "$R/repo" > "auto/$Q/plan.md"
"$CRUX/crux" auto check "auto/$Q/plan.md" --static
"$CRUX/crux" auto run "auto/$Q/plan.md"
