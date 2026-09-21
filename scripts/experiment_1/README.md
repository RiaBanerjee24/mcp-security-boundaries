# Experiment 1 (Gap 1) — interface hashing vs. a real server

Proves, mechanically, that a wire-level tool-definition hash (what six of
the seven defenses catalogued in `preprint.md` §3 rely on) misses a
schema-preserving behavior change — and that a file hash (what Tooldex's
`trust_store.py` pins) catches it.

**This runs against a real reference server, not a toy one.** The target
is Anthropic's own official `filesystem` MCP server
(`modelcontextprotocol/servers`, `src/filesystem`), vendored unmodified
into `../vendor/filesystem-server/`. Nothing about the target was written
for this experiment.

## What gets mutated

`readTextFileHandler`, defined *inline* in the server's own `index.ts`
(used by both the `read_file` and `read_text_file` tools). The mutation
adds one line — appending the OS username to every file read — without
touching the tool's registered name, description, or input schema a few
lines below in the same file. Interface byte-for-byte identical; behavior
different.

## Run it

```
cd mcp-security-boundaries
uv run --no-project --with mcp python3 scripts/experiment_1/run_experiment.py
```

Requires Node + npm (for the target server) and `npx tsx` available —
already installed in `../vendor/filesystem-server/node_modules` if you've
run `npm install` there once. The script runs the server's actual
TypeScript source directly via `tsx`, not a separately-built `dist/`, so
there's no risk of testing stale compiled output after editing the
source.

The script self-restores `index.ts` to its original content at the end —
safe to rerun.

## Or via Docker

Build context must be `scripts/` (this experiment needs the sibling
`vendor/filesystem-server/` directory too):

```
docker build -f scripts/experiment_1/Dockerfile -t rugpull-exp1 scripts/
docker run --rm rugpull-exp1
```

## Expected result

```
Wire-level hash:    UNCHANGED — mutation NOT detected
File hash:          CHANGED — mutation DETECTED
Actual tool output: CHANGED — real behavior differs
```

Confirms, on real production code rather than a hand-built example, the
limitation mcpseal, mcp-pin, and hardened-mcp-server each already
acknowledge about themselves.
