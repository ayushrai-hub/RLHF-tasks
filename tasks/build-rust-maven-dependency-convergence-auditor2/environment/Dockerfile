FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app

ENV PATH="/usr/local/cargo/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates=20230311+deb12u1 \
        python3=3.11.2-1+b1 \
        python3-pip=23.0.1+dfsg-1 \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc \
    && ln -sf /usr/local/cargo/bin/rustup /usr/local/bin/rustup \
    && printf '%s\n' 'export PATH="/usr/local/cargo/bin:$PATH"' > /etc/profile.d/cargo-path.sh

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    iniconfig==2.3.0 \
    packaging==26.2 \
    pluggy==1.6.0 \
    pygments==2.20.0 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY app/Cargo.toml app/Cargo.lock /app/
RUN mkdir -p src && printf 'fn main() {}\n' > src/main.rs
RUN cargo fetch --locked

COPY app/ /app/
RUN cargo build --locked
