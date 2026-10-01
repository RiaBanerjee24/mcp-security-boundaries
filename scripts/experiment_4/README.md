# Experiment 4 — the combined run

Not a new gap. This runs the same three mutations from Experiments 1-3
back to back, on the same real server, each checked against **one**
unified static layer (local-closure hash + the resolved dependency
directory, combined into a single hash-of-hashes) and **one** canary
layer (a fixed set of calls, compared against a baseline taken earlier
in the same session), under a single combined decision rule: flag if
either layer moves.

## Why this exists

Experiments 1-3 each show one mutation defeating one specific check.
This shows what happens when both layers run *together*, which is the
actual proposed architecture, not three separate ideas. The point is to
show that the two layers are complementary: each misses a scenario the
other catches, and only the combination catches all three.

## What runs

1. **Scenario 1** — the interface-preserving edit from Experiment 1
   (`readTextFileHandler` leaks the OS username).
2. **Scenario 2** — the dependency compromise from Experiment 2
   (`minimatch` always returns `true`).
3. **Scenario 3** — the dormant trigger from Experiment 3 (a call
   counter gates a leak starting on the 4th call, written once, never
   mutated again).

## How each layer is baselined

- **Static layer:** hashed once at approval, on the server as it stands
  then, and re-hashed after the scenario runs.
- **Canary layer (session-scoped, BASIL B1):** one server process, one
  session. The same fixed canary set runs in every scenario —
  `read_text_file` on `hello.txt` and `search_files` for `*.txt` — and is
  repeated 4 times. The first round is the baseline; every later round is
  compared against it. The canary never sees the server as it was at
  approval, and is never told which tool a scenario mutated.

Scenarios 1 and 2 mutate the server after approval, between sessions, so
the canary session only ever observes the already-mutated server.
Scenario 3's trigger is written before approval and fires within the
session.

Each scenario reports two booleans: did the static hash change, did the
canary check flag a difference. The target files are restored after
every scenario, even if it fails.

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
1 — interface-preserving edit    CHANGED    unchanged  CAUGHT
2 — dependency compromise        CHANGED    unchanged  CAUGHT
3 — dormant trigger              unchanged  CHANGED    CAUGHT
```

Each layer misses what the other catches:

- **Rows 1 and 2:** the static layer catches the change because its
  baseline comes from approval. The session-scoped canary misses it,
  because the change happened between sessions, so its baseline is
  taken from the already-mutated server and every round matches.
- **Row 3:** the static layer, including the lockfile-depth extension
  from Experiment 2, reports nothing, because nothing on disk changes
  after approval. The canary catches the trigger when it fires on the
  4th call.

Only the combined rule catches every row.
