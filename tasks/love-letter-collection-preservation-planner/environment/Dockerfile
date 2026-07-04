FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    tmux=3.3a-3 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes --no-deps \
    -r /tmp/requirements.lock

COPY Makefile /app/
COPY README.md /app/README.md
COPY heirloom-preservation/bin /app/heirloom-preservation/bin
COPY heirloom-preservation/lib /app/heirloom-preservation/lib
COPY heirloom-archive /app/heirloom-archive
COPY contracts /app/contracts
COPY scripts /app/scripts
COPY helpers /app/helpers

RUN mkdir -p /opt/verifier-scripts \
 && install -m 0755 /app/scripts/rebuild-heirloom-preservation /opt/verifier-scripts/rebuild-heirloom-preservation \
 && ln -sf /app/contracts /app/docs \
 && bash /app/scripts/build.sh \
 && mkdir -p /app/state /app/output /opt/verifier-fixtures

COPY opt-fixtures/ /tmp/opt-fixtures/
RUN cp -r /tmp/opt-fixtures/* /opt/verifier-fixtures/ \
 && rm -rf /tmp/opt-fixtures

ENV PATH="/app/heirloom-preservation/bin:/opt/verifier-scripts:/opt/verifier-venv/bin:${PATH}"
