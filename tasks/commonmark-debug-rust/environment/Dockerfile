FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Install system dependencies. build-essential supplies the linker/cc that
# rustc needs; curl + ca-certificates bootstrap rustup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        build-essential \
        ca-certificates \
        curl \
        git \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Install the Rust toolchain on top of the sanctioned python base. The runtime
# legitimately needs cargo (the verifier recompiles the agent's edited crate),
# so the toolchain is layered into the sanctioned final image via rustup rather
# than using a Rust runtime base. The build phase has internet; the version is
# pinned for reproducibility.
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:${PATH}
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --no-modify-path --profile minimal --default-toolchain 1.82.0 \
    && rustup component add rustfmt clippy \
    && chmod -R a+w "$RUSTUP_HOME" "$CARGO_HOME"

# Install Python verifier dependencies (PIN VERSIONS!) into a dedicated
# virtualenv at build time, so the verifier needs no network at runtime.
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.3.4 \
        pytest-json-ctrf==0.3.5

# Copy task files
COPY task_file /app/task_file

# Set up environment: warm the build cache, then drop the crate's own artifacts
# so the agent builds from clean source. The standard library and registry index
# stay cached, so the agent's offline build succeeds without network access.
RUN printf 'export PATH=/usr/local/cargo/bin:$PATH\n' > /etc/profile.d/cargo.sh \
    && cd /app/task_file && cargo build --release && cargo clean
ENV CARGO_NET_OFFLINE=true
ENV PATH="/opt/verifier-venv/bin:${PATH}"
