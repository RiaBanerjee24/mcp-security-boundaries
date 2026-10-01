# Experiment 3 (Gap 3) — self-contained, reproducible run.
#
# Same real reference server as Experiments 1 and 2. Bakes the Node/TS
# deps into the image at build time so the container needs no network
# access at run time.
#
# Build context must be `scripts/` (this Dockerfile needs the sibling
# `vendor/filesystem-server` directory too, not just its own folder):
#   docker build -f scripts/experiment_3/Dockerfile -t rugpull-exp3 scripts/
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/scripts

RUN uv pip install --system mcp
RUN uv run --no-project --with mcp python3 -c "import mcp"

COPY vendor/filesystem-server ./vendor/filesystem-server
RUN cd vendor/filesystem-server && npm install

COPY experiment_3/run_experiment.py ./experiment_3/run_experiment.py

WORKDIR /app/scripts/experiment_3
CMD ["python3", "run_experiment.py"]
