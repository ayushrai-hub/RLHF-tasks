FROM rust:1.85.1-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app
ENV PATH="/usr/local/cargo/bin:${PATH}"

COPY requirements.lock /tmp/requirements.lock

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        ca-certificates \
        python3 \
        python3-pip \
    && pip3 install --break-system-packages --require-hashes --no-deps --no-cache-dir -r /tmp/requirements.lock \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc

COPY app/ /app/app/
