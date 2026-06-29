# Canonical Rust base image for debugging tasks requiring cargo rebuild
FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV PATH="/usr/local/cargo/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip tmux asciinema && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY Cargo.toml Cargo.lock build.rs /app/
RUN mkdir src && echo "fn main(){}" > src/main.rs && \
    mkdir -p config data docs scripts && \
    echo 'aggregation_window_secs = 3600' > config/default.toml && \
    echo 'anomaly_threshold = 1.5' >> config/default.toml && \
    echo 'percentile_rounding = 4' >> config/default.toml && \
    echo 'outlier_zscore = 2.0' >> config/default.toml && \
    echo 'include_raw_data = false' >> config/default.toml && \
    echo 'calibration_factor = 1.0' >> config/default.toml && \
    echo 'enable_windowing = false' >> config/default.toml && \
    cargo build --release --locked 2>&1 && rm -rf src

COPY src/ /app/src/
COPY config/ /app/config/
RUN touch src/main.rs && cargo build --release --locked 2>&1

COPY data/ /app/data/
COPY docs/ /app/docs/

RUN mkdir -p /app/output

RUN echo 'export PATH="/usr/local/cargo/bin:$PATH"' >> /root/.bashrc
