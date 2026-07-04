FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Verifier-recording utilities required by the harness.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

# build-rev 2026-07-03a
# Task + verifier dependencies, baked at build time (the task runs fully offline).
RUN python -m pip install --no-cache-dir \
    numpy==2.3.1 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

# Provide the task inputs at /app/data (agent-visible). Tests/solution are NOT copied.
COPY data /app/data
