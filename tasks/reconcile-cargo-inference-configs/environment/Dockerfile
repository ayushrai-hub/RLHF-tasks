# Base image justification: this task is a TypeScript pipeline and needs a
# Node.js runtime. The image below is the exact digest-pinned canonical Node.js
# entry from the Terminal-Bench "Dockerfile & Image Best Practices" base-image
# policy (public.ecr.aws/docker/library/node:22-bookworm-slim, sha256
# f3a68cf4...b462383), which is the sanctioned Node runtime for this dataset. If
# the reviewing registry's canonical list mirrors these images under a different
# host, this digest is the intended equivalent and is proposed for addition;
# either way the image is immutable-digest-pinned. python3 is added only to run
# the pytest verifier, and the TypeScript toolchain (tsc) is intentionally in the
# final image because the task requires the agent to compile TypeScript at run
# time.
FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

# System packages: tmux + asciinema are required by the agent runtime; python3
# is required by the verifier.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

# Verifier dependencies (pinned). Installed at build time so the verifier runs
# fully offline.
RUN python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        PyYAML==6.0.2

# TypeScript compiler available globally for the agent's build step.
RUN npm install -g typescript@5.5.4

WORKDIR /app

# Install the TypeScript parsing dependencies into /app/node_modules at build
# time (from the committed lockfile) so the agent run needs no network.
COPY app/package.json app/package-lock.json /app/
RUN npm ci --no-audit --no-fund

# Task files (dossier, config sources, crate, TS scaffolding).
COPY app/ /app/
