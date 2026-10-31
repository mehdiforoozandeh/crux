# The taskhub: where work goes

*Reference for [`SKILL.md`](../SKILL.md). Read it before you add, finish or drop a task. The
boundary itself (knowledge in the tree, work in the taskhub) is in the core.*

A task is an **action**. If it is a claim about the world that could be true or false, it is
a hypothesis and belongs in the tree.

**What gets in — one question:** *would you be annoyed if this vanished next week?* If yes it
belongs in the taskhub, however small: "fetch the antibody lot from the ENCODE portal"
passes. If no it is session scratch ("re-read the checks on that hypothesis") and stays in
your own todo list, which may point *at* a task but never lands in the vault. Tasks can be
fine-grained; they cannot be ephemeral.
Rule of thumb: **a task should fit in one context window.**

**The moment a task would open a question, it stops being a task.** Make it a tree node
instead (`crux ask` or `crux hypothesize`). The engine cannot tell that a task's title is
really a question, so this rule is yours to keep.

**Output becomes evidence.** A task's output enters the tree only as evidence on a finding:
`crux finding <hid> ... -e tasks/<file>` or `-e results/<hid>/<file>`. No task waits for
anyone's acceptance; the accept gate on experiment tasks is removed (`crux task accept` and
`crux task review` print that they are removed).

Task bookkeeping is silent, like all bookkeeping: add, finish and drop without announcing it.

## The verbs

| verb | what it does |
|---|---|
| `task add` | append a task: `-c <category>` (from `crux task categories`), `--blocked-by <ids or None>` (required, so a missing edge is visible), `--ref <node>` for the node it serves (repeatable), `--parent <task>` for decomposition, `--why` for what it unblocks |
| `task done` | close a task; the engine refuses a `done` with no output that resolves. Link the real output, not the nearest thing that resolves |
| `task drop` | abandon a task; no output required |
| `task list` | query the taskhub; work the frontier (tasks whose blockers are all cleared) |
| `task show` | one task's record |
| `task categories` | the declared category list, or grow it |

External blockers are not a state: "waiting on cluster quota" is a dependency on a task called
**obtain cluster quota**.
