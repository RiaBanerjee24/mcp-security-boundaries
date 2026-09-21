# Experiment 1 — the interface-vs-implementation gap (Gap 1)

## What this demonstrates

An MCP tool's declared interface — name, description, input schema — can
be hashed and pinned to detect changes. This experiment tests whether
that alone is enough: can a tool's actual behavior change while its
declared interface stays byte-for-byte identical, and if so, does an
interface-level hash catch it? Does a file-content hash?

`echo_server.py` exposes one tool, `echo`. It's mutated once: the return
statement changes, but the tool's name, docstring (its description), and
signature (its input schema) stay byte-for-byte identical. Three signals
are compared before and after:

1. **Wire hash** — sha256 of the canonicalized `{name, description,
   inputSchema}` — the full declared interface. Expected unchanged.
2. **File hash** — sha256 of the script's own bytes, what Tooldex's
   `trust_store.py` actually pins. Expected changed.
3. **Real tool output** — an actual `tools/call`, not a static check.
   Expected changed.

## Folder structure

```
scripts/experiment_1/
├── echo_server.py       # the server under test — rewritten by
│                         # run_experiment.py on every run, restored to
│                         # v1 at the end (nothing to hand-edit here)
├── run_experiment.py     # orchestrator
└── README.md             # this file
```

## Running locally

Requires [`uv`](https://docs.astral.sh/uv/) and network access on first
run (to fetch `mcp`).

```bash
uv run --no-project --python 3.14 --with mcp python3 run_experiment.py
```

The script prints wire hash / file hash / real output for both the
original and mutated state, then a summary comparing all three. It
restores `echo_server.py` to its original content at the end — safe to
rerun repeatedly.

## Running via Docker

No local `uv`/Python setup needed — everything is baked into the image at
build time, including a pre-warmed `uv` cache so the container doesn't
need network access at run time either.

```bash
docker build -t experiment-1-gap1 .
docker run --rm experiment-1-gap1
```

## Reproducibility

**Expected output** (confirmed via `docker build` + `docker run`,
2026-09-20):

```
=== v1 (original): tool that echoes input unchanged ===
  wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
  file hash: 8f831f7c05511dd115dac2d4e0097a3dd38ed2255ff08644ef7bb20dee2c1520
  echo('hello') -> 'hello'

=== v2 (mutated): same name/description/schema, leaks a fixed marker ===
  wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
  file hash: 1d3b22f4e3b8ad8e64c197cb0246dcabe8c656cc7fe1588ee415ddf771803332
  echo('hello') -> 'hello | CANARY-LEAK-MARKER'

=== Result ===
  Wire-level hash: UNCHANGED — mutation NOT detected
  File hash:       CHANGED — mutation DETECTED
  Actual tool output: CHANGED — real behavior differs

  CONFIRMED: same-signature behavior change, invisible to wire-level
  pinning, caught by file-level pinning.
```

The file hash values depend on the exact bytes of `echo_server.py` at
each stage — they'll only match exactly if the file hasn't been edited
since this was recorded. The wire hash, the verdicts, and the leaked
marker in the output should match regardless of environment (local vs.
Docker vs. anyone else's machine), since the mutation uses a fixed
marker rather than an environment-dependent value like `$USER`.

## Interpreting the result


Interface-level hashing does not detect a same-signature behavior
change. File-content hashing does. This is demonstrated mechanically,
not just asserted.
