# Experiment 4 — combined run, self-contained, reproducible.
#
# Same real reference server as Experiments 1-3. Runs all three
# scenarios back to back against one unified static layer and one
# canary layer. Bakes the Node/TS deps into the image at build time so
# the container needs no network access at run time.
#
# Build context must be `scripts/`:
#   docker build -f scripts/experiment_4/Dockerfile -t rugpull-exp4 scripts/
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/scripts

RUN uv pip install --system mcp
RUN uv run --no-project --with mcp python3 -c "import mcp"

COPY vendor/filesystem-server ./vendor/filesystem-server
RUN cd vendor/filesystem-server && npm install

COPY experiment_4/run_experiment.py ./experiment_4/run_experiment.py

WORKDIR /app/scripts/experiment_4
CMD ["python3", "run_experiment.py"]
