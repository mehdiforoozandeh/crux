# Updating crux, and engine drift

*Reference for [`SKILL.md`](../SKILL.md). Read this when the PI asks you to update crux, or
when a command prints an update notice or an engine-drift warning.*

Any crux command may print `crux: vX.Y.Z is available …` on stderr (once a
day, from a cache — it never blocks and never installs anything). If the PI asks you to update:

1. **A clone install** (the notice names it — `git -C <root> pull --ff-only`): check the tree
   is clean and on the default branch first (`git -C <root> status --short --branch`). If it
   is dirty, on a feature branch, or the pull is not a fast-forward, **stop and say so** —
   do not stash, reset, force, or merge to make it apply.
2. **A skills install**: `npx skills update`.
3. Then tell the PI to re-run their command; the new engine takes effect on the next
   invocation, not the one in flight.

A newer engine may carry a newer vault format. The first command against an existing vault
will warn about **engine drift** and re-stamp it — surface that warning verbatim; if the PI
needs to reproduce recorded results exactly, the answer is to pin the old engine, not to
ignore the warning. `CRUX_NO_UPDATE_CHECK=1` switches the whole check off.
