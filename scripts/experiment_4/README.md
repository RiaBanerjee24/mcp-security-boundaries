# Experiment 4 — the combined run

Not a new gap. This runs the same three mutations from Experiments 1-3
back to back, on the same real server, each checked against **one**
unified static layer (local-closure hash + the resolved dependency
directory, combined into a single hash-of-hashes) and **one** canary
layer (a fixed-input call compared to an earlier baseline), under a
single combined decision rule: flag if either layer moves.

## Why this exists

Experiments 1-3 each show one mutation defeating one specific check.
This shows what happens when both layers run *together*, which is the
actual proposed architecture, not three separate ideas. The point isn't
to prove anything new — it's to show the one row where the static layer,
however complete, has nothing to report, and the canary layer is the
only reason that scenario gets caught at all.

## What runs

1. **Scenario 1** — the interface-preserving edit from Experiment 1
   (`readTextFileHandler` leaks the OS username).
2. **Scenario 2** — the dependency compromise from Experiment 2
   (`minimatch` always returns `true`).
3. **Scenario 3** — the dormant trigger from Experiment 3 (a call
   counter gates a leak starting on the 4th call, written once, never
   mutated again).

Each scenario mutates its target, probes the server, restores the
target, and reports two booleans: did the static hash change, did the
canary check flag a difference.

## Run it

```
cd mcp-security-boundaries
uv run --no-project --with mcp python3 scripts/experiment_4/run_experiment.py
```

Requires the shared vendored server in `../vendor/filesystem-server/`
(same as Experiments 1-3). Self-restores both mutated files (`index.ts`
and the vendored `minimatch`) at the end of each scenario — safe to
rerun.

## Or via Docker

Build context must be `scripts/`:

```
docker build -f scripts/experiment_4/Dockerfile -t rugpull-exp4 scripts/
docker run --rm rugpull-exp4
```

## Expected result

```
Scenario                         Static     Canary     Combined
1 — interface-preserving edit    CHANGED    CHANGED    CAUGHT
2 — dependency compromise        CHANGED    CHANGED    CAUGHT
3 — dormant trigger              unchanged  CHANGED    CAUGHT
```

Row 3 is the payoff: it is the only scenario where the static layer,
including the lockfile-depth extension from Experiment 2, reports
nothing wrong — because nothing on disk ever changed. The canary layer
catches it regardless, and the combined rule catches every row.
