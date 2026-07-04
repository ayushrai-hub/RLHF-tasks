FROM --platform=linux/amd64 public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS rust-toolchain

ENV CARGO_INCREMENTAL=0
WORKDIR /build

COPY Cargo.toml Cargo.lock /build/
COPY docs /build/docs
COPY src /build/src

RUN mkdir -p /build/bin \
    && cargo build --release --locked \
    && cp /build/target/release/rtcmctl /build/bin/rtcmctl

FROM --platform=linux/amd64 public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-venv \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/* \
    && tmux -V \
    && asciinema --version

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir -r /tmp/requirements.lock

ENV CARGO_INCREMENTAL=0
ENV PATH="/usr/local/cargo/bin:/opt/verifier-venv/bin:${PATH}"

WORKDIR /app

COPY Cargo.toml Cargo.lock README.md /app/
COPY docs /app/docs
COPY scripts /app/scripts
COPY src /app/src
COPY fixtures /app/fixtures

RUN mkdir -p /app/bin /app/runtime /app/state \
    && sed -i 's/\r$//' /app/scripts/*.sh \
    && chmod +x /app/scripts/build.sh /app/scripts/verifier-rebuild.sh \
    && cargo build --release --locked

COPY --from=rust-toolchain /build/bin/rtcmctl /app/bin/rtcmctl
RUN test -x /app/bin/rtcmctl
