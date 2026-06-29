# Canonical, digest-pinned Rust base image. The task ships a Rust crate
# (`kettleheat`) that the agent fixes and rebuilds with `cargo build --release`,
# so the runtime stage uses the sanctioned Rust toolchain image directly.
FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

COPY wheels/ /opt/python-wheels/
COPY requirements.lock /opt/python-wheels/requirements.lock
RUN apt-get update && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        coreutils \
        git \
        patch \
        python3 \
        python-is-python3 \
        python3-pip \
        ripgrep \
        sed \
        tmux \
        util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-index \
        --find-links /opt/python-wheels \
        --require-hashes \
        --no-deps \
        -r /opt/python-wheels/requirements.lock

# Expose the Rust toolchain on the agent's login-shell PATH.
RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc

WORKDIR /app
COPY repo/ /app/

# Warm the build so the agent's post-edit rebuild is incremental and the build
# cache stays in the image. Then initialize a git repo so the agent's edit
# tooling works at runtime.
RUN cargo build --release --locked \
    && git init -q \
    && git config user.email task@example.com \
    && git config user.name task \
    && git add -A \
    && git commit -q -m "initial task state"
