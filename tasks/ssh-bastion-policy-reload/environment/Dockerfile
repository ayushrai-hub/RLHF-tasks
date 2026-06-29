FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

WORKDIR /app

# terminus-2 agent harness requires tmux + asciinema in the image (not at verifier runtime).
# Verifier runtime: pytest==7.2.1 (apt package python3-pytest=7.2.1-2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    patch=2.7.6-7 \
    python3=3.11.2-1+b1 \
    python3-pytest=7.2.1-2 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/*

COPY package.json /app/package.json
COPY src /app/src
COPY fixtures /app/fixtures
COPY docs /app/docs

RUN mkdir -p /app/output
