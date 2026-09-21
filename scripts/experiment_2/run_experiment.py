"""
scripts/experiment_2/run_experiment.py

Gap 2: does Tooldex's real file-hash pinning — which walks only the entry
point's own local directory tree — detect a mutation delivered through a
module resolved from OUTSIDE that tree? Does a whole-dependency-closure
hash (this project's proposed fix)?

Setup: entry/entry_server.py imports process() from external/logic.py, a
SIBLING directory to entry/, not a subfolder of it — so Tooldex's real
directory walk (which only descends from the entry point's own folder)
never reaches it. Only logic.py is ever mutated; entry_server.py never
changes.

Calls Tooldex's real trust_store.py — not a reimplementation. Run against
the real, versioned, PyPI-published release (byte-identical to this
project's local copy, verified 2026-09-20):
    uv run --with tooldex==1.0.2 --with mcp python3 run_experiment.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import os
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from tooldex.core.discovery import trust_store
from tooldex.core.models.server import MCPServer

HERE = Path(__file__).resolve().parent
ENTRY_PATH = HERE / "entry" / "entry_server.py"
SCRIPTS_DIR = Path(__file__).resolve().parents[1]  # scripts/
LOGIC_PATH = SCRIPTS_DIR / "tmp" / "experiment_2_external" / "logic.py"



# Isolate the trust store before anything else runs — never touch the
# real ~/.tooldex/trust_store.json.
trust_store._STORE_PATH = HERE / "isolated_trust_store.json"

V1_LOGIC = '''"""
scripts/experiment_2/external/logic.py

The only file mutated in this experiment. Lives in a directory that is a
SIBLING of entry_server.py's own folder, not a subfolder of it — that's
what keeps it outside Tooldex's real file-hash walk, which only descends
from the entry point's own directory tree.
"""


def process(text: str) -> str:
    return text
'''

# Same function name, same signature — only the executed behavior changes.
# A fixed marker instead of $USER: deterministic across every environment
# (local, Docker, anyone else's machine), and avoids anything shaped like
# a real credential prefix that could trip a secret scanner on the repo.
V2_LOGIC = '''"""
scripts/experiment_2/external/logic.py

The only file mutated in this experiment. Lives in a directory that is a
SIBLING of entry_server.py's own folder, not a subfolder of it — that's
what keeps it outside Tooldex's real file-hash walk, which only descends
from the entry point's own directory tree.
"""


def process(text: str) -> str:
    return text + " | CANARY-LEAK-MARKER"
'''


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closure_hash(paths: list[Path]) -> str:
    """Hash-of-hashes: sha256 of each file, sorted, concatenated, re-hashed."""
    digests = sorted(file_sha256(p) for p in paths)
    return hashlib.sha256("".join(digests).encode()).hexdigest()


def wire_hash(tool) -> str:
    canonical = json.dumps(
        {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


async def probe():
    params = StdioServerParameters(
        command="uv",
        args=["run", "--script", str(ENTRY_PATH)],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            echo_tool = next(t for t in tools if t.name == "echo")
            call = await session.call_tool("echo", {"text": "hello"})
            output = call.content[0].text if call.content else None
            return wire_hash(echo_tool), output


async def main() -> int:
    server = MCPServer(
        name="whole-closure-demo",
        transport="stdio",
        command="uv",
        args=["run", "--script", str(ENTRY_PATH)],
    )

    # --- v1: baseline ---
    LOGIC_PATH.write_text(V1_LOGIC)
    trust_store.set_decision(server, "allow")  # Tooldex's real approval call
    wire1, out1 = await probe()
    closure1 = closure_hash([ENTRY_PATH, LOGIC_PATH])
    print("=== v1 (original) ===")
    print(f"  wire hash: {wire1}")
    print(f"  closure hash: {closure1}")
    print(f"  output: {out1!r}")

    # --- v2: mutate only the external module ---
    LOGIC_PATH.write_text(V2_LOGIC)
    tooldex_says_changed = trust_store.files_changed_since_approval(server)  # Tooldex's real drift check
    wire2, out2 = await probe()
    closure2 = closure_hash([ENTRY_PATH, LOGIC_PATH])
    print("\n=== v2 (mutated — external module changed, entry point untouched) ===")
    print(f"  wire hash: {wire2}")
    print(f"  closure hash: {closure2}")
    print(f"  output: {out2!r}")
    print(f"  Tooldex's real files_changed_since_approval(): {tooldex_says_changed}")

    LOGIC_PATH.write_text(V1_LOGIC)  # restore, keep the repo clean

    print("\n=== Result ===")
    print(f"  Wire-level hash:                    "
          f"{'UNCHANGED — mutation NOT detected' if wire1 == wire2 else 'changed — detected'}")
    print(f"  Tooldex real entry-point-tree check: "
          f"{'says UNCHANGED — mutation NOT detected (the point)' if not tooldex_says_changed else 'says CHANGED — detected'}")
    print(f"  Whole-closure hash:                 "
          f"{'unchanged' if closure1 == closure2 else 'CHANGED — mutation DETECTED'}")
    print(f"  Real output:                        "
          f"{'unchanged' if out1 == out2 else 'CHANGED — real behavior differs'}")

    ok = (wire1 == wire2) and (not tooldex_says_changed) and (closure1 != closure2) and (out1 != out2)
    if ok:
        print("\n  CONFIRMED: a mutation delivered outside the entry point's local")
        print("  directory tree is invisible to wire hashing AND to Tooldex's real")
        print("  file-hash pinning, but caught by the whole-closure hash.")
        return 0
    print("\n  UNEXPECTED — re-check the experiment.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
