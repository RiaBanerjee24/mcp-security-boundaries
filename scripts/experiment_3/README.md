# Experiment 3 (Gap 3) — a dormant trigger vs. every static hash

Proves that a static hash — wire-level, or a local-closure hash, or
even one extended to cover package-manager dependencies (the fix from
Experiment 2) — cannot detect a malicious trigger that was present in a
tool's code from the moment it was deployed and never touches disk
again afterward. Not because the hash is incomplete, but because there
is nothing on disk for it to see change.

This models a real, documented pattern: a server that behaves honestly
for a number of calls before defecting once some threshold is crossed —
the same shape reported as a real incident ("a server behaving normally
for three calls before changing behavior on the fourth") and formalized
independently as a benchmarked threat class in published research on
staged MCP server compromise.

## How this is structurally different from Experiments 1 and 2

Those two show a hash *missing* a change because it isn't looking in the
right place (the file itself, or a dependency). This one shows a hash
having *nothing to look at*: the file is written once, deployed, and
never rewritten again for the rest of the run. Only observing actual
behavior across repeated calls — not any hash, however complete — can
catch it.

## Setup

The same real `filesystem` reference server used by Experiments 1 and
2, with one change written *once*: `readTextFileHandler` gains a
module-level call counter and a threshold-gated branch — normal
behavior for the first 3 calls, a leak appended starting on the 4th.
Unlike Experiments 1 and 2, this file is never mutated mid-run — the
counter's state lives in the running process's memory, not on disk,
which is exactly what makes it invisible to a hash taken at any point.

One server process, one live session, four calls made within it — not
a fresh process per call, because the trigger's state has to persist
across calls the way it would for a real long-running MCP session.

## Four signals

1. **Wire hash** — taken once, mid-session — expected unchanged (the
   interface was never touched, then or ever).
2. **Local-closure hash** — taken once before the session and once
   after — expected **identical both times**. This is the load-bearing
   result: not "unchanged between two versions" as in Experiments 1/2,
   but "unchanged because there was never a second version."
3. **Canary output hash** — the first call's output, hashed and treated
   as a baseline; every later call's output compared against it —
   expected to match for calls 1–3 and mismatch on call 4.
4. **Real output** — expected identical for calls 1–3, different on
   call 4.

## Run it

```
cd mcp-security-boundaries
uv run --no-project --with mcp python3 scripts/experiment_3/run_experiment.py
```

Requires the shared vendored server in `../vendor/filesystem-server/`
(same as Experiments 1 and 2). Self-restores the file to its original
content at the end — safe to rerun.

## Or via Docker

Build context must be `scripts/`:

```
docker build -f scripts/experiment_3/Dockerfile -t rugpull-exp3 scripts/
docker run --rm rugpull-exp3
```

## Expected result

```
Local-closure hash across the whole session: IDENTICAL before/after
Calls 1-3 match the canary baseline: True
Call 4 (past the threshold) differs from baseline: True
```

Confirms that no static hash — however complete — can reach this class
of attack by construction, and that only a dynamic check, comparing a
tool's own behavior against its own prior behavior, closes it.
