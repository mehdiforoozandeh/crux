#!/usr/bin/env bash
#
# install.sh — install the crux skills onto this machine.
#
# Symlinks every skill under ./skills/ into your agent's skills dirs so the agent
# picks them up: crux, crux-wiki, crux-cockpit, evolve-crux, and any future crux
# skills. Drop a new skill folder under skills/ and it's installed automatically.
#
# Default targets: ~/.claude/skills (Claude Code) and ~/.agents/skills (the shared
# dir Cursor, Codex, Windsurf, and Copilot CLI read).
#
# Usage:
#   ./install.sh                    # install all crux skills into both default dirs
#   SKILLS_DIR=/tmp/x ./install.sh  # install into exactly one custom dir instead
#
# Safe by design: only ever creates/refreshes symlinks it manages; a real
# (non-symlink) folder of the same name is left untouched and reported.

if [ -z "${BASH_VERSION:-}" ]; then
  echo "install.sh: run with bash: ./install.sh" >&2
  exit 1
fi
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${SKILLS_DIR:-}" ]]; then
  TARGETS=("$SKILLS_DIR")
else
  TARGETS=("$HOME/.claude/skills" "$HOME/.agents/skills")
fi

linked=0; skipped=0
for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  for d in "$REPO_DIR"/skills/*/; do
    d="${d%/}"; name="$(basename "$d")"; dest="$target/$name"
    if [[ ! -f "$d/SKILL.md" ]]; then
      echo "  ! skip $name — no SKILL.md" >&2; skipped=$((skipped+1)); continue
    fi
    if [[ -e "$dest" && ! -L "$dest" ]]; then
      echo "  ! skip $name — a real folder exists at $dest (left untouched)" >&2; skipped=$((skipped+1)); continue
    fi
    ln -sfn "$d" "$dest"
    echo "  ✓ $name → $target"; linked=$((linked+1))
  done
done

echo "== crux: $linked linked, $skipped skipped =="
echo "Skills are symlinks into this clone — keep it in place (if you move it, re-run ./install.sh)."
echo "Restart / reload your agent to pick up new skills."
