FROM rust:1.86-bookworm@sha256:878ca0e8df1305dcbbfffac5bb908cce6a4bc5f6b629c518e7112645ee8851d4

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates=20230311+deb12u1 \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY Cargo.toml /app/environment/Cargo.toml
COPY src /app/environment/src
COPY data /app/environment/data
COPY scripts /app/environment/scripts

RUN chmod +x /app/environment/scripts/run_probe.sh \
    && cargo build --manifest-path /app/environment/Cargo.toml

RUN mkdir -p /app/output
