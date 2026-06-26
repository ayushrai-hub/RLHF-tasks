FROM rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip pkg-config tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
    pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY Cargo.toml Cargo.lock /app/
COPY src/ /app/src/
COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY scripts/ /app/scripts/

RUN cargo build --release
RUN mkdir -p /app/output
