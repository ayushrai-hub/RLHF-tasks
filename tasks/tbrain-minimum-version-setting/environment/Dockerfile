FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS rust-toolchain

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV CARGO_HOME=/usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV PATH=/usr/local/cargo/bin:${PATH}
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY --from=rust-toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust-toolchain /usr/local/rustup /usr/local/rustup

RUN for bin in /usr/local/cargo/bin/*; do \
        ln -sf "$bin" "/usr/local/bin/$(basename "$bin")"; \
    done

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        build-essential \
        ca-certificates \
        coreutils \
        git \
        patch \
        ripgrep \
        sed \
        tmux \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        pytest==8.4.2 \
        pytest-json-ctrf==0.3.5

RUN rustup toolchain install 1.89.0 --profile minimal \
    && rustup default 1.89.0

COPY repo/ /app/

WORKDIR /app

RUN cargo fetch --locked \
    && cargo build --locked --bin just \
    && git init -q \
    && git config user.email task@example.com \
    && git config user.name task \
    && git add -A \
    && git commit -q -m "initial task state" \
    && tmux -V \
    && asciinema --version
