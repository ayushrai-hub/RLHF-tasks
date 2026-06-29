FROM --platform=linux/amd64 public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm -f /tmp/requirements.txt

ENV PATH="/usr/local/cargo/bin:/opt/verifier-venv/bin:/usr/local/bin:${PATH}"
ENV CARGO_INCREMENTAL=0

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY crates/ballcore/Cargo.toml crates/ballcore/Cargo.toml
COPY crates/ballctl/Cargo.toml crates/ballctl/Cargo.toml

RUN mkdir -p crates/ballcore/src crates/ballctl/src \
 && echo "pub fn placeholder(){}" > crates/ballcore/src/lib.rs \
 && echo "fn main(){}" > crates/ballctl/src/main.rs \
 && cargo fetch --locked

ENV CARGO_NET_OFFLINE=true

COPY crates/ /app/crates/
COPY docs/ /app/docs/
COPY fixtures/ /app/fixtures/
COPY scripts/ /app/scripts/
COPY README.md /app/README.md
COPY verifier-fixtures/ /opt/verifier-fixtures/

RUN sed -i 's/\r$//' /app/scripts/*.sh \
 && chmod +x /app/scripts/reset-state.sh \
 && cargo build --release --locked -p ballctl \
 && install -m 0755 /app/target/release/ballctl /usr/local/bin/ballctl \
 && mkdir -p /app/output /app/state \
 && /app/scripts/reset-state.sh

