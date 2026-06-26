FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        git \
        ripgrep \
        make \
        procps \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

COPY app/ /app/
RUN chmod +x /app/scripts/replay-chunks.sh /app/scripts/soak-chunks.sh /app/scripts/dev.sh /app/scripts/lint.sh \
    && cargo fetch --locked \
    && cargo test --workspace --no-run --locked \
    && cargo build --release --locked -p streamd

ENV PATH="/usr/local/cargo/bin:/usr/local/bin:/usr/bin:${PATH}"
