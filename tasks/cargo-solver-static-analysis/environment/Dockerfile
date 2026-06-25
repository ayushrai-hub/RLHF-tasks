FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# tmux + asciinema are required by the harness; gawk provides the AWK engine the
# auditor relies on (match() third-arg captures, gensub). coreutils gives a
# stable `sort` for deterministic TSV output.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        coreutils \
        gawk \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Verifier-only Python deps baked in at build time (no network at run/verify time).
RUN python -m pip install --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

# Workspace, broken auditor, and the long-context dossier. Solution/ and tests/
# are intentionally NOT copied into the image.
COPY wavebench/ /app/wavebench/
COPY scripts/ /app/scripts/
COPY docs/ /app/docs/

RUN mkdir -p /app/reports
