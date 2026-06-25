FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS rust_toolchain

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/cargo/bin:${PATH}"
ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --break-system-packages --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY --from=rust_toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust_toolchain /usr/local/rustup /usr/local/rustup

WORKDIR /app

COPY Cargo.toml Cargo.lock /app/
COPY src /app/src
COPY g1 /app/g1
COPY g2 /app/g2
COPY g3 /app/g3
COPY data /app/data
COPY config /app/config

RUN mkdir -p /app/output /app/data/seed \
    && cargo build --release --locked

ENV TRACEFOLD_OUT=/app/output/tracefold_report.json
ENV TRACEFOLD_SEED=/app/data/seed/scenarios.json

