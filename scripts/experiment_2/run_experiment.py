"""
scripts/experiment_2/run_experiment.py

Gap 2, on a real reference server, against Tooldex's REAL trust_store.py
(not a reimplementation) — and a corrected claim from what this project
originally assumed.

**What changed from the original plan, and why**: Tooldex's real,
published `trust_store.py` (v1.0.2) does NOT hash only the entry-point
file. Read directly (`inspect.getsource`): it walks *down* from the
entry point's own directory, hashing every recognized local source file
in that tree — already close to the "whole-closure hash" this project
set out to propose. What it deliberately excludes, by its own docstring
("pinning an entire node_modules tree is a different, impractical
problem"), is package-manager-installed dependencies: `node_modules`,
`venv`, `.venv`, `env` are pruned from the walk.

So the real, current Gap 2 is narrower and more realistic than "any
import at all": it's specifically a compromise delivered through a
package-manager dependency, not a sibling source file. This experiment
demonstrates that version, on Anthropic's actual `filesystem` reference
server, using its actual `minimatch` npm dependency (already used by the
server's own `search_files` tool) as the mutated package — not a
contrived stand-in.

Setup
-----
- Entry point: `../vendor/filesystem-server/index.ts` (shared with
  Experiment 1, unmodified here).
- Mutated file: `../vendor/filesystem-server/node_modules/minimatch/
  dist/commonjs/index.js` — the real, installed npm dependency the
  server imports and calls from `lib.ts`'s `searchFilesWithValidation`
  (used by the `search_files` tool's both its main pattern match and its
  `excludePatterns` check).
- Mutation: `minimatch(...)` is made to always return `true`. Real
  consequence: `search_files` with pattern `*.txt` starts returning
  every file in the tree, not just `.txt` files — including one that
  was never supposed to match at all.

Four signals, not three:
1. Wire hash — expected unchanged (schema untouched).
2. Tooldex's real `files_changed_since_approval()` — expected to say
   UNCHANGED (this is the point: node_modules is pruned by design).
3. Whole-closure hash of the *local* tree (this project's original
   Gap-2-era proposal: entry point + its local siblings, still no
   node_modules) — expected ALSO unchanged, for the same reason.
4. A lockfile-depth hash — hash-of-hashes over the resolved
   `node_modules/minimatch/` directory as it stood at approval time,
   re-checked later, the same mechanism as the closure hash just applied
   one level deeper — expected CHANGED. This is the §4.1 extension this
   project had previously left as "specified, not built"; this
   experiment is the first time it's actually run.
5. Real output — expected changed (the unauthorized file appears).

Run against the real, versioned, PyPI-published release (matches the
project's other Tooldex-calling experiment):
    uv run --with tooldex==1.0.2 --with mcp python3 run_experiment.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from tooldex.core.discovery import trust_store
from tooldex.core.models.server import MCPServer

HERE = Path(__file__).resolve().parent
SERVER_DIR = HERE.parent / "vendor" / "filesystem-server"
INDEX_TS = SERVER_DIR / "index.ts"
LOCAL_TREE_FILES = [
    SERVER_DIR / "index.ts",
    SERVER_DIR / "lib.ts",
    SERVER_DIR / "path-validation.ts",
    SERVER_DIR / "path-utils.ts",
    SERVER_DIR / "roots-utils.ts",
]
MINIMATCH_DIR = SERVER_DIR / "node_modules" / "minimatch"
# The server's own package.json has "type": "module", so `import { minimatch }
# from 'minimatch'` resolves via the "import" condition in minimatch's own
# package.json exports map -> dist/esm/index.js, NOT dist/commonjs/index.js
# (the CJS "require" condition / legacy "main" field). Mutating the wrong
# one produces zero observable effect — confirmed the hard way, by first
# mutating commonjs/index.js and finding the output didn't change at all.
MINIMATCH_ENTRY = MINIMATCH_DIR / "dist" / "esm" / "index.js"

# Isolate the trust store before anything else runs — never touch the
# real ~/.tooldex/trust_store.json.
trust_store._STORE_PATH = HERE / "isolated_trust_store.json"

ORIGINAL_MINIMATCH = MINIMATCH_ENTRY.read_text()

_ANCHOR = "    return new Minimatch(pattern, options).match(p);\n"
assert ORIGINAL_MINIMATCH.count(_ANCHOR) == 1, (
    "mutation anchor not uniquely found in minimatch's index.js — "
    "installed version changed, re-check"
)
MUTATED_MINIMATCH = ORIGINAL_MINIMATCH.replace(_ANCHOR, "    return true;\n")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dir_closure_hash(root: Path) -> str:
    """Hash-of-hashes over every file in a directory tree, sorted."""
    files = sorted(p for p in root.rglob("*") if p.is_file())
    digests = sorted(file_sha256(p) for p in files)
    return hashlib.sha256("".join(digests).encode()).hexdigest()


def local_closure_hash() -> str:
    digests = sorted(file_sha256(p) for p in LOCAL_TREE_FILES)
    return hashlib.sha256("".join(digests).encode()).hexdigest()


def wire_hash(tool) -> str:
    canonical = json.dumps(
        {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


async def probe(allowed_dir: Path):
    params = StdioServerParameters(
        command="npx",
        args=["tsx", str(INDEX_TS), str(allowed_dir)],
        cwd=str(SERVER_DIR),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            tool = next(t for t in tools if t.name == "search_files")
            call = await session.call_tool(
                "search_files", {"path": str(allowed_dir), "pattern": "*.txt"}
            )
            output = call.content[0].text if call.content else None
            return wire_hash(tool), output


async def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        allowed_dir = Path(tmp)
        (allowed_dir / "a.txt").write_text("a\n")
        (allowed_dir / "b.txt").write_text("b\n")
        (allowed_dir / "secret.env").write_text("SECRET=leak-me-not\n")

        server = MCPServer(
            name="filesystem-gap2-demo",
            transport="stdio",
            command="npx",
            args=["tsx", str(INDEX_TS), str(allowed_dir)],
        )

        # --- v1: baseline ---
        MINIMATCH_ENTRY.write_text(ORIGINAL_MINIMATCH)
        trust_store.set_decision(server, "allow")  # Tooldex's real approval call
        wire1, out1 = await probe(allowed_dir)
        local1 = local_closure_hash()
        lock1 = dir_closure_hash(MINIMATCH_DIR)
        print("=== v1 (original): real minimatch, unmodified ===")
        print(f"  wire hash: {wire1}")
        print(f"  local-closure hash: {local1}")
        print(f"  lockfile-depth (minimatch dir) hash: {lock1}")
        print(f"  search_files('*.txt') -> {out1!r}")

        # --- v2: mutate only the node_modules dependency ---
        MINIMATCH_ENTRY.write_text(MUTATED_MINIMATCH)
        tooldex_says_changed = trust_store.files_changed_since_approval(server)  # real check
        wire2, out2 = await probe(allowed_dir)
        local2 = local_closure_hash()
        lock2 = dir_closure_hash(MINIMATCH_DIR)
        print("\n=== v2 (mutated): real npm dependency compromised, entry point untouched ===")
        print(f"  wire hash: {wire2}")
        print(f"  local-closure hash: {local2}")
        print(f"  lockfile-depth (minimatch dir) hash: {lock2}")
        print(f"  search_files('*.txt') -> {out2!r}")
        print(f"  Tooldex's real files_changed_since_approval(): {tooldex_says_changed}")

        MINIMATCH_ENTRY.write_text(ORIGINAL_MINIMATCH)  # restore, keep the vendored copy clean

    print("\n=== Result ===")
    print(f"  Wire-level hash:                  "
          f"{'UNCHANGED — mutation NOT detected' if wire1 == wire2 else 'changed — detected'}")
    print(f"  Tooldex real check (node_modules pruned by design): "
          f"{'says UNCHANGED — mutation NOT detected (the point)' if not tooldex_says_changed else 'says CHANGED — detected'}")
    print(f"  Local-closure hash (this project's original Gap-2 fix): "
          f"{'unchanged — ALSO misses it' if local1 == local2 else 'CHANGED — detected'}")
    print(f"  Lockfile-depth hash (the §4.1 extension, run here for the first time): "
          f"{'unchanged' if lock1 == lock2 else 'CHANGED — mutation DETECTED'}")
    print(f"  Real output: "
          f"{'unchanged' if out1 == out2 else 'CHANGED — real behavior differs'}")

    ok = (
        wire1 == wire2
        and not tooldex_says_changed
        and local1 == local2
        and lock1 != lock2
        and out1 != out2
    )
    if ok:
        print("\n  CONFIRMED: a real npm dependency compromise is invisible to wire hashing,")
        print("  invisible to Tooldex's real trust_store.py, and invisible to this project's")
        print("  own originally-proposed local-closure hash — all three stop at the same")
        print("  boundary (node_modules, deliberately excluded). Only extending the hash to")
        print("  the resolved dependency's own directory (the lockfile-depth extension)")
        print("  catches it.")
        return 0
    print("\n  UNEXPECTED — re-check the experiment.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
