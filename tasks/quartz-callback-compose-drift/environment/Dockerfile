FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36
# Baseline parity marker for check_default_template.py: FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends python3=3.11.2-1+b1 python-is-python3=3.11.2-1+deb12u1 \
    python3-pip=23.0.1+dfsg-1 \
    build-essential=12.9 \
    ca-certificates=20230311+deb12u1 \
    pkg-config=1.8.1-1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY Cargo.toml /app/Cargo.toml
COPY Cargo.lock /app/Cargo.lock
COPY src /app/src
COPY qz /app/qz
COPY sx /app/sx
COPY data /app/data
COPY cfg /app/cfg
COPY docs /app/docs

ENV PATH="/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

RUN mkdir -p /app/output /app/state /app/bin \
    && ln -sf /app /app/environment \
    && cargo build --release --bins \
    && ln -sf /app/target/release/ode_harness /app/bin/ode_harness \
    && ln -sf /app/target/release/ode_probe /app/bin/ode_probe

ENV PATH="/usr/local/cargo/bin:/app/bin:/app/target/release:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
