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
    && mkdir -p /var/tmp/tmux /app/output /app/replay-state /app/tools /app/cases /app/environment \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

COPY runtime/tmux.conf /etc/tmux.conf
COPY requirements.lock /tmp/requirements.txt

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes --no-deps \
        -r /tmp/requirements.txt

WORKDIR /app/environment

COPY Cargo.toml Cargo.lock ./
RUN cargo fetch --locked

COPY cli /app/environment/cli
COPY internal /app/environment/internal
COPY p7 /app/environment/p7
COPY d3 /app/environment/d3
COPY d5 /app/environment/d5
COPY c4 /app/environment/c4
COPY f2 /app/environment/f2
COPY pack /app/environment/pack
COPY cases /app/cases
COPY docs /app/docs

RUN ln -sf /app/docs /app/environment/docs \
    && cargo build --release --locked

RUN mkdir -p /app/tools /app/environment/tools \
    && ln -sf /app/environment/target/release/r8_run /app/tools/r8_run \
    && ln -sf /app/environment/target/release/r8_emit /app/tools/r8_emit \
    && ln -sf /app/environment/target/release/r8_recover /app/tools/r8_recover \
    && ln -sf /app/environment/target/release/r8_sample /app/tools/r8_sample \
    && ln -sf /app/environment/target/release/r8_run /app/environment/tools/r8_run \
    && ln -sf /app/environment/target/release/r8_emit /app/environment/tools/r8_emit \
    && ln -sf /app/environment/target/release/r8_recover /app/environment/tools/r8_recover \
    && ln -sf /app/environment/target/release/r8_sample /app/environment/tools/r8_sample \
    && chmod +x /app/tools/r8_run /app/tools/r8_emit /app/tools/r8_recover /app/tools/r8_sample \
    && chmod +x /app/environment/d5/bootstrap.sh

ENV PATH="/opt/verifier-venv/bin:/usr/local/cargo/bin:/app/environment/target/release:/app/tools:/app/environment:${PATH}"
