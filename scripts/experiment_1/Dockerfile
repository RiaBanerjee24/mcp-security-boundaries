# Experiment 1 (Gap 1) — self-contained, reproducible run.
#
# Runs the mutation test against a real reference server (Anthropic's
# official `filesystem` MCP server), not a toy one. Bakes both the
# Python MCP client deps and the Node/TypeScript server deps into the
# image at build time so the container needs no network access at run
# time.
#
# Build context must be `scripts/` (this Dockerfile needs the sibling
# `vendor/filesystem-server` directory too, not just its own folder):
#   docker build -f scripts/experiment_1/Dockerfile -t rugpull-exp1 scripts/
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Node is not in the base image; install it for the target server.
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/scripts

RUN uv pip install --system mcp
RUN uv run --no-project --with mcp python3 -c "import mcp"

COPY vendor/filesystem-server ./vendor/filesystem-server
RUN cd vendor/filesystem-server && npm install

COPY experiment_1/run_experiment.py ./experiment_1/run_experiment.py

WORKDIR /app/scripts/experiment_1
CMD ["python3", "run_experiment.py"]
