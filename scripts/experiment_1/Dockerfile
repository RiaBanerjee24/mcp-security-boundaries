# Experiment 1 (Gap 1) — self-contained, reproducible run.
#
# Bakes mcp into the image at build time and pre-warms uv's cache so the
# container needs no network access at run time — including for the
# child `uv run --script` invocation of echo_server.py, which resolves
# its own tiny isolated environment from its inline PEP723 header.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN uv pip install --system mcp
RUN uv run --no-project --with mcp python3 -c "import mcp"

COPY echo_server.py ./scripts/experiment_1/echo_server.py
COPY run_experiment.py ./scripts/experiment_1/run_experiment.py

WORKDIR /app/scripts/experiment_1
CMD ["python3", "run_experiment.py"]
