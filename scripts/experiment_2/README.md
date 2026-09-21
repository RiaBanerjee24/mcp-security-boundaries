# Experiment 2 (Gap 2) — a real dependency compromise vs. a local-closure hash

Proves, against a real reference server's real npm dependency and an
existing local-closure hash implementation (not a reimplementation),
that a package-manager-delivered compromise is invisible to hash-based
checks that stop at the local file tree — and that extending the hash
one level deeper, into the resolved dependency itself, catches it.

## What a local-closure hash actually checks

Read directly from real, published source (`inspect.getsource`): a
local-closure hash walks *down* from the entry point's own directory,
hashing every recognized local source file in that tree, but excludes
package-manager-installed dependency directories — `node_modules`,
`venv`, `.venv`, `env`.

So the gap this experiment targets is specifically **a compromise
delivered through a package-manager dependency**, not an arbitrary
imported file. It demonstrates exactly that, using a dependency the
target server already actually uses.

## What gets mutated

`minimatch`, a real npm package the `filesystem` reference server
imports and calls from `lib.ts`'s `searchFilesWithValidation` (used by
the `search_files` tool, both for its main pattern match and its
`excludePatterns` check). The mutation makes `minimatch()` always return
`true`.

The server's `package.json` has `"type": "module"`, so
`import { minimatch } from 'minimatch'` resolves via minimatch's own
`exports` map's `"import"` condition — `dist/esm/index.js` — not
`dist/commonjs/index.js` (the `"require"` condition / legacy `main`
field). If you extend this to a different dependency, mutate whichever
file that package's own `exports` map actually resolves for the way it's
imported — test in isolation first to confirm the mutation is live
before trusting any downstream result.

## Real consequence

`search_files` with pattern `*.txt` starts returning every file in the
searched directory, not just `.txt` files — including one that was
never supposed to match at all (`secret.env` in this demo).

## Four signals compared

1. **Wire hash** — expected unchanged (schema untouched).
2. **A local-closure hash's real drift check** — the actual published
   implementation, called directly, not reimplemented — expected to say
   unchanged (`node_modules` excluded).
3. **Local-closure hash** (entry point + its local siblings, no
   `node_modules`) — expected *also* unchanged, for the same reason.
4. **Lockfile-depth hash** — hash-of-hashes over the resolved
   `node_modules/minimatch/` directory, established as a baseline and
   re-checked later, the same mechanism as the closure hash applied one
   level deeper — expected changed.
5. **Real output** — expected changed.

## Run it

```
cd mcp-security-boundaries
uv run --no-project --with tooldex==1.0.2 --with mcp python3 scripts/experiment_2/run_experiment.py
```

Requires Node/npm (shared vendored server in `../vendor/filesystem-server/`,
same as Experiment 1) and the `tooldex` package from PyPI, used here only
as a real, existing local-closure hash implementation to test against.

Self-restores the mutated file at the end — safe to rerun.

## Or via Docker

Build context must be `scripts/`:

```
docker build -f scripts/experiment_2/Dockerfile -t rugpull-exp2 scripts/
docker run --rm rugpull-exp2
```

## Expected result

```
Wire-level hash:                  UNCHANGED
Local-closure hash's real check:  UNCHANGED (node_modules excluded — the point)
Local-closure hash (recomputed):  unchanged — also misses it
Lockfile-depth hash:              CHANGED — detected
Real output:                      CHANGED
```

Confirms that a local-closure hash is itself incomplete against the most
realistic real-world delivery mechanism for this class of attack — a
compromised dependency, not a hand-placed sibling file — and that
closing it needs the lockfile-depth extension specifically, not just
"hash more files."
