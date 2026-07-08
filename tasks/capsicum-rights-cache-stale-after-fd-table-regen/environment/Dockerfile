FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    ncurses-term=6.4-4 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
&& mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

COPY runtime/tmux.conf /etc/tmux.conf

COPY requirements.lock /tmp/requirements.txt
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes --no-deps \
        -r /tmp/requirements.txt

RUN mkdir -p /opt/verifier/bin \
    && ln -sf /opt/verifier-venv/bin/pytest /opt/verifier/bin/pytest

RUN mkdir -p /app/output /app/replay-state /app/tools /app/cases /app/environment

COPY Cargo.toml Cargo.lock /app/environment/
COPY cli /app/environment/cli
COPY src /app/environment/src
COPY spool /app/environment/spool
COPY drift /app/environment/drift
COPY notch /app/environment/notch
COPY gauge /app/environment/gauge
COPY phase /app/environment/phase
COPY pack /app/environment/pack
COPY cases /app/cases
COPY docs /app/environment/docs

WORKDIR /app/environment

RUN test -x /usr/local/cargo/bin/cargo \
    && cargo build --release --locked

RUN mkdir -p /app/tools /app/environment/tools \
    && ln -sf /app/environment/target/release/k7_invoke /app/tools/k7_invoke \
    && ln -sf /app/environment/target/release/k7_z2 /app/tools/k7_z2 \
    && ln -sf /app/environment/target/release/k7_recover /app/tools/k7_recover \
    && ln -sf /app/environment/target/release/k7_invoke /app/environment/tools/k7_invoke \
    && ln -sf /app/environment/target/release/k7_z2 /app/environment/tools/k7_z2 \
    && ln -sf /app/environment/target/release/k7_recover /app/environment/tools/k7_recover \
    && chmod +x /app/tools/k7_invoke /app/tools/k7_z2 /app/tools/k7_recover \
    && chmod +x /app/environment/phase/bootstrap.sh

ENV PATH="/opt/verifier-venv/bin:/usr/local/cargo/bin:/app/environment/target/release:/app/tools:/app/environment:${PATH}"
