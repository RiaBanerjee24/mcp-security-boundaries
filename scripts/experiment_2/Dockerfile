# Experiment 2 (Gap 2) — self-contained, reproducible run.
#
# Runs against a real reference server's real npm dependency, and
# against Tooldex's real, published trust_store.py — not
# reimplementations of either. Bakes both the Python and Node/TS deps
# into the image at build time so the container needs no network access
# at run time.
#
# Build context must be `scripts/` (this Dockerfile needs the sibling
# `vendor/filesystem-server` directory too, not just its own folder):
#   docker build -f scripts/experiment_2/Dockerfile -t rugpull-exp2 scripts/
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/scripts

RUN uv pip install --system mcp tooldex==1.0.2
RUN uv run --no-project --with mcp --with tooldex==1.0.2 python3 -c "import mcp; from tooldex.core.discovery import trust_store"

COPY vendor/filesystem-server ./vendor/filesystem-server
RUN cd vendor/filesystem-server && npm install

COPY experiment_2/run_experiment.py ./experiment_2/run_experiment.py

WORKDIR /app/scripts/experiment_2
CMD ["python3", "run_experiment.py"]
