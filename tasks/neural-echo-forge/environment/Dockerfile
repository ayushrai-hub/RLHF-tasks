FROM --platform=linux/amd64 public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    build-essential \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir \
    pytest==9.0.3 \
    pytest-json-ctrf==0.5.0

RUN mkdir -p /opt/verifier-scripts
COPY scripts/verifier-rebuild.sh /opt/verifier-scripts/rebuild-tool
COPY scripts/echo-mutate.py /opt/verifier-scripts/echo-mutate
RUN chmod +x /opt/verifier-scripts/rebuild-tool /opt/verifier-scripts/echo-mutate

ENV PATH="/usr/local/cargo/bin:/opt/verifier-venv/bin:/opt/verifier-scripts:${PATH}"
ENV CARGO_INCREMENTAL=0
WORKDIR /app

COPY docs/ /app/docs/
COPY data/ /app/data/
COPY cmd/ /app/cmd/
COPY src/ /app/src/
COPY Cargo.toml /app/Cargo.toml
COPY Cargo.lock /app/Cargo.lock

RUN cargo fetch \
 && cargo build --release --locked \
 && cp target/release/neural-echo-forge /app/neural-echo-forge \
 && mkdir -p /app/output /app/state
