FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:/opt/verifier/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    build-essential=12.9 \
    ca-certificates=20230311+deb12u1 \
    curl=7.88.1-10+deb12u14 \
    git=1:2.39.5-0+deb12u3 \
    libssl3=3.0.20-1~deb12u1 \
    pkg-config=1.8.1-1 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/* \
    && tmux -V \
    && asciinema --version

RUN python3 -m venv /opt/verifier \
    && /opt/verifier/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.81.0 --profile minimal \
    && chmod -R a+w /usr/local/rustup /usr/local/cargo

COPY Cargo.toml /app/environment/Cargo.toml
COPY Cargo.lock /app/environment/Cargo.lock
COPY rust-toolchain.toml /app/environment/rust-toolchain.toml
COPY src /app/environment/src
COPY core /app/environment/core
COPY codec /app/environment/codec
COPY journal /app/environment/journal
COPY flow /app/environment/flow
COPY docs /app/environment/docs
COPY data /app/environment/data
COPY config /app/environment/config
COPY tools /app/environment/tools
COPY ci /app/environment/ci

RUN cd /app/environment && CARGO_NET_OFFLINE=false cargo fetch --locked \
    && chmod +x /app/environment/tools/*.sh /app/environment/ci/matrix_regress.sh
