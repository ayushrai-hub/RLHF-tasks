FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS builder

WORKDIR /build
COPY app/Cargo.toml app/Cargo.lock ./
COPY app/src ./src
RUN mkdir -p /build/bin \
    && cargo build --release --locked \
    && install -m 0755 /build/target/release/mission-ingest /build/bin/mission-ingest \
    && install -m 0755 /build/target/release/mission-export /build/bin/mission-export \
    && install -m 0755 /build/target/release/serde-f64-fmt /build/bin/serde-f64-fmt

FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="mavlink-mission-upload-sequence-auditor"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        build-essential \
        ca-certificates \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
    pytest==9.0.3 \
    pytest-json-ctrf==0.5.0

RUN mkdir -p /opt/verifier-scripts

COPY --from=builder /usr/local/cargo /usr/local/cargo
COPY --from=builder /usr/local/rustup /usr/local/rustup
ENV PATH="/usr/local/cargo/bin:/app/bin:${PATH}"
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo
ENV TZ=UTC

WORKDIR /app
COPY app/ /app/
COPY --from=builder /build/bin/mission-ingest /app/bin/mission-ingest
COPY --from=builder /build/bin/mission-export /app/bin/mission-export
COPY --from=builder /build/bin/serde-f64-fmt /opt/verifier-scripts/serde-f64-fmt

COPY scripts/gen_sample_mseq.py /tmp/gen_sample_mseq.py
RUN chmod +x /app/scripts/build.sh /app/scripts/oracle-build.sh \
    && mkdir -p /app/data /app/output /app/bin \
    && python3 /tmp/gen_sample_mseq.py --sample-dir /app/data \
    && rm -f /tmp/gen_sample_mseq.py
