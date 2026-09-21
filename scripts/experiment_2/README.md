# Experiment 2 — the whole-closure-hash gap (Gap 2)

## What this demonstrates

Tooldex's real file-hash pinning (`trust_store.py`) hashes the entry
point's *entire local directory tree*, not just the single entry file. 
This experiment asks the next, narrower question: 
**does that boundary have an edge of its own?**

`entry/entry_server.py` imports a function from `logic.py`, which lives
in `scripts/tmp/experiment_2_external/` — a directory that is *not* a
descendant of `entry/`'s own folder, and therefore never reached by
Tooldex's real directory walk (which only descends from wherever the
entry point itself lives). Only `logic.py` is ever mutated; the entry
point's declared interface (name, description, schema) and its own file
bytes never change.

Four signals are compared before and after the mutation:

1. **Wire hash** — the tool's declared interface. Expected unchanged.
2. **Tooldex's real `files_changed_since_approval()`** — called against
   the actual installed `tooldex` package, not a reimplementation.
   Expected to say *unchanged* — this is the boundary being demonstrated.
3. **Whole-closure hash** — this project's proposed fix: `sha256` of the
   sorted set of `sha256(entry_point)` and `sha256(logic.py)`. Expected
   changed.
4. **Real tool output** — an actual `tools/call`, not a static check.
   Expected changed.

## Folder structure

```
scripts/experiment_2/
├── entry/
│   └── entry_server.py       # entry point — never mutated
├── run_experiment.py          # orchestrator
└── README.md                  # this file

scripts/tmp/experiment_2_external/
└── logic.py                   # the only file mutated — runtime-managed,
                                # gitignored, rewritten by run_experiment.py
                                # on every run (nothing to hand-edit here)
```

`scripts/tmp/` is gitignored — its contents are pure runtime scratch, not
static, so there's nothing to commit or maintain there beyond the
directory existing.

## Running locally

Requires [`uv`](https://docs.astral.sh/uv/) and network access on first
run (to fetch `tooldex` and `mcp`).

```bash
mkdir -p ../tmp/experiment_2_external   # one-time setup, from this folder
uv run --no-project --python 3.14 --with tooldex==1.0.2 --with mcp python3 run_experiment.py
```

The script prints wire hash / Tooldex's real hash-check / closure hash /
real output for both the original and mutated state, then a summary
comparing all four. It restores `logic.py` to its original content at the
end — safe to rerun repeatedly.

## Running via Docker

No local `uv`/Python setup needed — everything is baked into the image at
build time.

```bash
docker build -t experiment-2-gap2 .
docker run --rm experiment-2-gap2
```

## Reproducibility

`tooldex==1.0.2` is the real, versioned, PyPI-published Tooldex release . 
Anyone running the exact commands above gets the identical code this experiment's results.

**Expected output** (confirmed via `docker build` + `docker run`, 2026-09-20):

```
=== v1 (original) ===
  wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
  closure hash: c40dd43a174cc8f1b11d5c6ef3ea39f6a01662f46c6f8c77edf3335515721daa
  output: 'hello'

=== v2 (mutated — external module changed, entry point untouched) ===
  wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
  closure hash: 90b5b9b67eeb1ed7e2eeb20da5b7c6ad4f63483594aef738d8e841b3895c0adb
  output: 'hello | CANARY-LEAK-MARKER'
  Tooldex's real files_changed_since_approval(): False

=== Result ===
  Wire-level hash:                    UNCHANGED — mutation NOT detected
  Tooldex real entry-point-tree check: says UNCHANGED — mutation NOT detected (the point)
  Whole-closure hash:                 CHANGED — mutation DETECTED
  Real output:                        CHANGED — real behavior differs

  CONFIRMED: a mutation delivered outside the entry point's local
  directory tree is invisible to wire hashing AND to Tooldex's real
  file-hash pinning, but caught by the whole-closure hash.
```

Since the closure hash depends on the exact bytes of `entry_server.py` and
`logic.py`, it will only match exactly if neither file has been edited
since this was recorded — the wire hash, the "unchanged"/"changed"
verdicts, and the leaked marker in the output should match regardless.

## Interpreting the result

A mutation delivered through a
dependency outside the entry point's own directory tree is invisible,
but caught by the proposed whole-closure hash.
