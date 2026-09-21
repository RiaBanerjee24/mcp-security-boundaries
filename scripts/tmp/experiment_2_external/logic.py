"""
scripts/experiment_2/external/logic.py

The only file mutated in this experiment. Lives in a directory that is a
SIBLING of entry_server.py's own folder, not a subfolder of it — that's
what keeps it outside Tooldex's real file-hash walk, which only descends
from the entry point's own directory tree.
"""


def process(text: str) -> str:
    return text
