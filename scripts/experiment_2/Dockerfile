# Experiment 2 (Gap 2) — self-contained, reproducible run.
#
# Bakes tooldex==1.0.2 (the real, versioned, PyPI-published release,
# verified byte-identical to this project's local copy) and mcp into the
# image at build time, and pre-warms uv's cache so the container needs no
# network access at run time — including for the child `uv run --script`
# invocation of entry_server.py, which resolves its own tiny isolated
# environment from its inline PEP723 header.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN uv pip install --system "tooldex==1.0.2" mcp

# Pre-warm uv's package cache for `mcp` so entry_server.py's own
# `uv run --script` call (spawned as a child process by run_experiment.py)
# can resolve from cache instead of needing network at container run time.
RUN uv run --no-project --with mcp python3 -c "import mcp"

# Preserve the exact relative directory depth run_experiment.py and
# entry_server.py compute their paths from at runtime
# (Path(__file__).resolve().parents[N]) — don't flatten this layout.
COPY entry/ ./scripts/experiment_2/entry/
COPY run_experiment.py ./scripts/experiment_2/run_experiment.py
RUN mkdir -p ./scripts/tmp/experiment_2_external

WORKDIR /app/scripts/experiment_2
CMD ["python3", "run_experiment.py"]
