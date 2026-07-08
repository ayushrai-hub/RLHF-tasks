FROM rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS rust_builder

WORKDIR /build
COPY xk9 /build/xk9
WORKDIR /build/xk9
RUN cargo generate-lockfile && cargo build --release

FROM golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update     && apt-get install -y --no-install-recommends         asciinema=2.2.0-1         ca-certificates=20230311+deb12u1         python3=3.11.2-1+b1         python3-venv=3.11.2-1+b1         tmux=3.3a-3     && mkdir -p /var/tmp/tmux /logs/verifier /app/output /app/var/grad /app/environment/build     && chmod 1777 /var/tmp/tmux     && chmod 777 /logs/verifier /app/output /app/var /app/environment/build     && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv     && /opt/verifier-venv/bin/pip install --no-cache-dir         pytest==8.4.1         pytest-json-ctrf==0.3.5     && ln -sf /opt/verifier-venv/bin/pytest /usr/local/bin/pytest

COPY --from=rust_builder /usr/local/rustup /usr/local/rustup
COPY --from=rust_builder /usr/local/cargo /usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV PATH=/usr/local/cargo/bin:/opt/verifier-venv/bin:/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY go.mod /app/environment/go.mod
COPY xk9 /app/environment/xk9
COPY --from=rust_builder /build/xk9/Cargo.lock /app/environment/xk9/Cargo.lock
COPY --from=rust_builder /build/xk9/target /app/environment/xk9/target
COPY internal /app/environment/internal
COPY cmd /app/environment/cmd
COPY data /app/environment/data
COPY docs /app/environment/docs
COPY scripts /app/environment/scripts

RUN chmod 755 /app/environment/scripts/rebuild.sh     && /app/environment/scripts/rebuild.sh
