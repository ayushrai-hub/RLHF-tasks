FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup \
    CARGO_NET_OFFLINE=true \
    RUST_BACKTRACE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /app

COPY requirements.lock /tmp/requirements.lock

RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc \
    && printf 'Acquire::http::Timeout "120";\nAcquire::Retries "3";\n' > /etc/apt/apt.conf.d/99timeout \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        iproute2 \
        procps \
        python-is-python3 \
        python3 \
        python3-pip \
        tmux \
    && python3 -m pip install --no-cache-dir --break-system-packages \
        --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm -rf /var/lib/apt/lists/* /tmp/requirements.lock

# Pre-vendored crates (rust-vendor.tar.gz; no cargo fetch/network during image build).
COPY rust-deps/Cargo.toml rust-deps/Cargo.lock /opt/rust-deps/
COPY rust-vendor.tar.gz /tmp/rust-vendor.tar.gz
RUN mkdir -p /opt/vendor \
    && tar -xzf /tmp/rust-vendor.tar.gz -C /opt/vendor \
    && rm -f /tmp/rust-vendor.tar.gz

RUN mkdir -p /usr/local/cargo \
    && printf '%s\n' \
        '[source.crates-io]' \
        'replace-with = "vendored-sources"' \
        '' \
        '[source.vendored-sources]' \
        'directory = "/opt/vendor"' \
        '' \
        '[net]' \
        'offline = true' \
        > /usr/local/cargo/config.toml

RUN mkdir -p /app/state /app/bin /app/spec

COPY spec/ /app/spec/
