FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

# Install verifier dependencies (Python + Rust toolchain) at build time so the
# container can run the test suite with no network access. tmux and asciinema are
# required by the Harbor harness to drive the agent.
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        curl \
        ca-certificates \
        build-essential \
        pkg-config \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
    && curl --proto '=https' --tlsv1.2 -sSf --retry 3 --max-time 120 https://sh.rustup.rs \
       | sh -s -- -y --default-toolchain 1.86.0 --profile minimal \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:$PATH"
RUN ln -sf /root/.cargo/bin/cargo /usr/local/bin/cargo \
    && ln -sf /root/.cargo/bin/rustc /usr/local/bin/rustc \
    && ln -sf /root/.cargo/bin/rustfmt /usr/local/bin/rustfmt

# Pre-install all test/verifier dependencies (test.sh must not reach the network).
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --break-system-packages --require-hashes --no-deps -r /tmp/requirements.lock

COPY task_file /app/task_file
RUN mkdir -p /app/task_file/output_data

# Warm the cargo registry + dependency build cache so agent / oracle builds don't
# need to re-download crates from crates.io on every run.
RUN cd /app/task_file/dispatcher \
    && cargo fetch \
    && cargo build --release \
    && rm -rf target/release/dispatcher target/release/deps/dispatcher-*
