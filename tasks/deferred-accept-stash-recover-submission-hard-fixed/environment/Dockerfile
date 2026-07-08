# Rust 1.85-slim official image with the canonical digest.
FROM docker.io/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV PATH=/usr/local/cargo/bin:/usr/bin:/bin

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends python3=3.11.2-1+b1 python3-venv=3.11.2-1+b1 \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    ncurses-term=6.4-4 \
    tmux=3.3a-3 \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && ln -sf /usr/local/cargo/bin/cargo /usr/bin/cargo \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY runtime/tmux.conf /etc/tmux.conf
COPY runtime/dispatch.toml /app/environment/runtime/dispatch.toml
COPY Cargo.toml Cargo.lock /app/environment/
COPY docs /app/environment/docs
COPY samples /app/environment/samples
COPY ops /app/environment/ops
COPY prime /app/environment/prime
COPY carry /app/environment/carry
COPY rift /app/environment/rift
COPY loom /app/environment/loom
COPY ring /app/environment/ring
COPY coil /app/environment/coil
COPY vault /app/environment/vault
COPY span /app/environment/span
COPY mesh /app/environment/mesh
COPY seal /app/environment/seal
COPY fuse /app/environment/fuse
COPY src /app/environment/src

WORKDIR /app
