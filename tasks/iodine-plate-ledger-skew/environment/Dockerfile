FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates=20230311+deb12u1 \
    curl=7.88.1-10+deb12u14 \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ENV CHECK_RUNNER=pytest \
    CHECK_REPORTER=pytest-json-ctrf

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "${CHECK_RUNNER}==8.4.1" \
    "${CHECK_REPORTER}==0.3.5"

RUN ln -sf /usr/bin/python3 /usr/local/bin/python

RUN printf '%s\n' \
    '#!/bin/sh' \
    'if [ "$1" = "pytest" ]; then' \
    '  shift' \
    '  exec python -m pytest "$@"' \
    'fi' \
    'exec python -m "$@"' \
    > /usr/local/bin/uvx \
    && chmod +x /usr/local/bin/uvx

WORKDIR /app

# Workspace members: m3l (iodine-plate), r8k — not w5m/q1r legacy names.
COPY Cargo.toml /app/Cargo.toml
COPY Cargo.lock /app/Cargo.lock
COPY rust-toolchain.toml /app/rust-toolchain.toml
COPY m3l /app/m3l
COPY r8k /app/r8k
COPY fixtures /app/fixtures
COPY config /app/config
COPY docs /app/docs
COPY data /app/data
COPY profiles /app/profiles
COPY policy /app/policy

RUN mkdir -p /app/var/cache/head /app/var/cache/gen /app/output \
    && ln -s /app /app/environment

RUN cargo build --release
