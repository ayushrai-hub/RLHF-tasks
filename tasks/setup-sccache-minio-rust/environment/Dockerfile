FROM rust:1.85.1-slim-bookworm@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app
ENV CARGO_TERM_COLOR=never \
    PATH="/usr/local/cargo/bin:/usr/local/bin:/usr/bin:${PATH}"

ARG MINIO_VERSION=RELEASE.2025-04-22T22-12-26Z
ARG MC_VERSION=RELEASE.2025-04-16T18-13-26Z
ARG SCCACHE_VERSION=0.10.0
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        coreutils \
        curl \
        git \
        procps \
        python3 \
        python3-venv \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && printf '%s\n' 'export PATH="/usr/local/cargo/bin:${PATH}"' > /etc/profile.d/cargo-path.sh \
    && chmod 644 /etc/profile.d/cargo-path.sh \
    && ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc

RUN case "${TARGETARCH}" in \
        amd64) MINIO_ARCH=linux-amd64; SCCACHE_ARCH=x86_64-unknown-linux-musl ;; \
        arm64) MINIO_ARCH=linux-arm64; SCCACHE_ARCH=aarch64-unknown-linux-musl ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl -fsSL "https://dl.min.io/server/minio/release/${MINIO_ARCH}/archive/minio.${MINIO_VERSION}" -o /usr/local/bin/minio \
    && chmod +x /usr/local/bin/minio \
    && curl -fsSL "https://dl.min.io/client/mc/release/${MINIO_ARCH}/archive/mc.${MC_VERSION}" -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc \
    && curl -fsSL "https://github.com/mozilla/sccache/releases/download/v${SCCACHE_VERSION}/sccache-v${SCCACHE_VERSION}-${SCCACHE_ARCH}.tar.gz" -o /tmp/sccache.tgz \
    && tar -xzf /tmp/sccache.tgz -C /tmp \
    && mv "/tmp/sccache-v${SCCACHE_VERSION}-${SCCACHE_ARCH}/sccache" /usr/local/bin/sccache \
    && chmod +x /usr/local/bin/sccache \
    && rm -rf /tmp/sccache.tgz "/tmp/sccache-v${SCCACHE_VERSION}-${SCCACHE_ARCH}" \
    && sccache --version

RUN python3 -m venv /opt/test-venv \
    && /opt/test-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY Cargo.toml Cargo.lock rust-toolchain.toml /app/
COPY .cargo/ /app/.cargo/
COPY crates/ /app/crates/

RUN cargo fetch --locked

COPY config/ /app/config/
COPY docs/ /app/docs/
COPY README.md /app/README.md

RUN git init -q -b main \
    && git config user.email "seed@example.com" \
    && git config user.name "seed" \
    && git add . \
    && git commit -q -m "seed meridian workspace"

RUN mkdir -p /var/minio/data /var/run/minio /var/cache/sccache-meridian /app/reports
