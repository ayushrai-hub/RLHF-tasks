FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        patch \
        python3 \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --require-hashes --no-deps --no-cache-dir -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY task_file /app/task_file

ENV PATH=/opt/venv/bin:/usr/local/cargo/bin:${PATH} CARGO_NET_OFFLINE=true
RUN cd /app/task_file && cargo build --release --locked && cargo clean
