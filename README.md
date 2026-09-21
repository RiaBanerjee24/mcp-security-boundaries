# Where MCP Tool Integrity Checks Stop

Research code and preprint draft for a field-level audit of MCP "rug-pull"
defenses, plus four experiments demonstrating three nested gaps every
current defense leaves open — on a real, vendored, unmodified MCP
reference server (Anthropic's official `filesystem` server), not a toy
example.

**Start here:** [`preprint.md`](preprint.md) is the current draft.
[`claude/progress-report.md`](claude/progress-report.md) is the current
source of truth on project status. `research-plan.md` and
`claude/preprint-frame.md` are stale pre-pivot drafts, kept for reference
only.

## The three gaps

1. **Gap 1 — interface vs. implementation.** A wire-level tool-definition
   hash (name, description, schema) misses a behavior change that leaves
   the interface byte-for-byte identical.
2. **Gap 2 — local closure vs. package-manager dependency.** Hashing a
   tool's own local source tree (what Tooldex's `trust_store.py` actually
   does) misses a compromise delivered through a real npm dependency,
   which is deliberately excluded from that hash by design.
3. **Gap 3 — any static hash vs. a dormant trigger.** A threshold-gated
   trigger written once at deploy time and never touched again is
   invisible to a hash taken at any point, however complete, because
   nothing on disk ever changes.

A fourth experiment runs all three mutations together against one unified
static+canary architecture, showing the combination catches everything
neither layer catches alone.

## Repo layout

```
preprint.md                      current draft
research-plan.md                 stale, pre-pivot — reference only
claude/progress-report.md        current source of truth on project status
claude/preprint-frame.md         stale, pre-pivot — reference only
scripts/vendor/filesystem-server vendored, unmodified copy of Anthropic's
                                  official filesystem MCP reference server
                                  (the shared target for all 4 experiments)
scripts/experiment_1/            Gap 1
scripts/experiment_2/            Gap 2
scripts/experiment_3/            Gap 3
scripts/experiment_4/            combined run
```

Each experiment directory has its own `README.md` with the exact mutation,
expected result, and run instructions in detail.

## Running the experiments

Each experiment is self-contained: it mutates one real file in the
vendored server, probes it, compares detection signals, then restores the
file — safe to rerun. None require network access at run time (Docker
images bake all dependencies in at build time).

### All four at once, via Docker Compose

```
docker compose up --build
```

Runs all four experiments back to back, each in its own container, and
prints their results in sequence. Requires nothing but Docker — no local
Python, Node, or npm setup.

Run a single one:

```
docker compose up --build experiment_1
```

### Individually, via Docker

```
docker build -f scripts/experiment_1/Dockerfile -t rugpull-exp1 scripts/
docker run --rm rugpull-exp1
```

(substitute `experiment_2` / `_3` / `_4` as needed — build context is
always `scripts/`, since every experiment shares the vendored server in
`scripts/vendor/filesystem-server/`)

### Natively, without Docker

Requires Python 3.12+ with [`uv`](https://docs.astral.sh/uv/), and
Node/npm for the vendored target server:

```
cd scripts/vendor/filesystem-server && npm install && cd -
uv run --no-project --with mcp python3 scripts/experiment_1/run_experiment.py
uv run --no-project --with mcp --with tooldex==1.0.2 python3 scripts/experiment_2/run_experiment.py
uv run --no-project --with mcp python3 scripts/experiment_3/run_experiment.py
uv run --no-project --with mcp python3 scripts/experiment_4/run_experiment.py
```

## License

MIT — see [`LICENSE`](LICENSE).
