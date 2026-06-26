# Justification: Multi-stage build — compile Rust binaries in canonical rust:1.85-slim; pytest verifier runs on canonical python:3.13-slim-bookworm runtime.
FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS builder

WORKDIR /app/environment

COPY . .

RUN cargo build --release --locked

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tmux \
        asciinema \
        build-essential \
        pkg-config \
        libssl3 \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY --from=builder /usr/local/cargo /usr/local/cargo
COPY --from=builder /usr/local/rustup /usr/local/rustup
ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo

RUN mkdir -p /app/output

COPY . /app/environment

COPY --from=builder /app/environment/target/release/ctl_r7 /usr/local/bin/ctl_r7
COPY --from=builder /app/environment/target/release/chain_ref /usr/local/bin/chain_ref

RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc

ENV PATH=/usr/local/bin:/usr/local/cargo/bin:${PATH}

CMD ["echo", "environment ready"]
