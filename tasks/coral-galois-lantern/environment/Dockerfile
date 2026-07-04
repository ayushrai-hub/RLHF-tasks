# Canonical Terminal-Bench Rust base image (digest-pinned).
# Single stage on purpose: the agent must author and compile a Rust project
# inside the container, so the Rust toolchain (cargo/rustc + linker) has to be
# present in the final runtime image. This is the documented exception to
# check_no_build_tools_in_runtime ("unless the task explicitly requires the
# agent to use them").
FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app

# tmux + asciinema are required by the agent runtime.
# gcc/libc dev provide the system linker cargo invokes on the gnu target.
# python3 + pip host the pytest verifier.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        gcc \
        libc6-dev \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Verifier dependencies (pinned). Installed at build time only.
RUN python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

# Keep cargo fully offline at runtime so a stray dependency fails fast
# instead of reaching for the network (the task is standard-library only).
ENV CARGO_NET_OFFLINE=true

# Task files (sample input only — no solution, no tests).
COPY app/ /app/
