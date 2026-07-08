FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ncurses-term=6.4-4 \
    bash=5.2.15-2+b13 \
    ca-certificates=20230311+deb12u1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

COPY runtime/tmux.conf /etc/tmux.conf

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY Cargo.toml Cargo.lock /app/environment/
WORKDIR /app/environment
RUN mkdir -p agg ckpt cache report ref cli flow config fixtures scripts docs runtime \
    && echo 'pub fn stub() {}' > lib.rs

RUN cargo generate-lockfile || true

COPY lib.rs /app/environment/
COPY agg /app/environment/agg
COPY ckpt /app/environment/ckpt
COPY cache /app/environment/cache
COPY report /app/environment/report
COPY ref /app/environment/ref
COPY flow /app/environment/flow
COPY cli /app/environment/cli
COPY config /app/environment/config
COPY fixtures /app/environment/fixtures
COPY scripts /app/environment/scripts
COPY docs /app/environment/docs
COPY entrypoint.sh /entrypoint.sh

RUN cargo build --release --bin stream-stats \
    && install -m 0755 target/release/stream-stats /usr/local/bin/stream-stats \
    && chmod +x /app/environment/scripts/build_stats.sh /app/environment/scripts/prep_run.sh /entrypoint.sh \
    && mkdir -p /app/output /app/var /logs/verifier /logs/agent

ENTRYPOINT ["/entrypoint.sh"]
CMD ["sleep", "infinity"]
