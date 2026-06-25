FROM --platform=linux/amd64 public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
 asciinema \
 ca-certificates \
 python3 \
 python3-pip \
 python3-venv \
 tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
 && rm /tmp/requirements.lock

RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
 && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc

RUN printf '%s\n' \
    'export PATH="/usr/local/cargo/bin:/usr/local/bin:/opt/verifier-venv/bin:${PATH}"' \
    'export CARGO_INCREMENTAL=0' \
    > /etc/profile.d/terminus-toolchain.sh

ENV PATH="/usr/local/cargo/bin:/usr/local/bin:/opt/verifier-venv/bin:${PATH}"
ENV CARGO_INCREMENTAL=0

WORKDIR /app

COPY Cargo.toml Cargo.lock ./
COPY src/ src/
COPY bin/ bin/
COPY fixtures/ fixtures/
COPY verifier-fixtures/ verifier-fixtures/
COPY state/ state/
COPY docs/ docs/

RUN chmod +x /app/bin/oracle-build-ota.sh /app/bin/rebuild-ota

RUN cargo build --release --locked \
 && mkdir -p /app/bin /app/state/ota /app/output /opt/verifier-fixtures/ota-trap \
 && cp target/release/ota_chain /app/bin/ota-chain \
 && cp /app/verifier-fixtures/ota-trap/stage-plan.json /opt/verifier-fixtures/ota-trap/stage-plan.json
