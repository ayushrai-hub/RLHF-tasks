FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    bash \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==9.0.3 pytest-json-ctrf==0.5.0

WORKDIR /app

COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY blocks ./blocks
COPY config ./config
COPY schemas ./schemas
COPY geokit ./geokit
COPY data ./data
COPY docs ./docs
COPY scripts ./scripts
COPY deploy ./deploy

RUN cargo build --release \
 && mkdir -p /app/bin /app/state /app/output /opt/verifier-scripts \
 && install -m 0755 target/release/geosynth /app/bin/geosynth \
 && chmod +x /app/scripts/rebuild-geosynth-engine.sh \
    /app/scripts/finalize-discovery-atlas.sh \
 && cp /app/scripts/rebuild-geosynth-engine.sh /opt/verifier-scripts/rebuild-geosynth-engine.sh

ENV PATH="/usr/local/cargo/bin:/app/bin:${PATH}"
