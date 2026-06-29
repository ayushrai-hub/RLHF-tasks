FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36 AS builder

WORKDIR /app

# Install Python for tests
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages pytest==8.3.2 pytest-timeout==2.3.1 pytest-json-ctrf==0.5.0

# Copy workspace manifest
COPY Cargo.toml ./

# Copy all crate sources (BUGGY versions)
COPY parse/ parse/
COPY aggregate/ aggregate/
COPY classify/ classify/
COPY emit/ emit/
COPY tools/nfa_verify tools/nfa_verify/
COPY scripts/rebuild.sh scripts/

# Build the buggy workspace
RUN cargo build --workspace --release

FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app

# Install Python and pytest for verifier tests
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv tmux asciinema && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /app/.testenv && /app/.testenv/bin/pip install --no-cache-dir pytest==8.3.2 pytest-timeout==2.3.1 pytest-json-ctrf==0.5.0
ENV PATH="/app/.testenv/bin:/usr/local/cargo/bin:${PATH}"

# Copy buggy binary
COPY --from=builder /app/target/release/nfa_verify /app/nfa_verify

# Copy sources and traces
COPY Cargo.toml Cargo.toml
COPY Cargo.lock Cargo.lock
COPY parse/ parse/
COPY aggregate/ aggregate/
COPY classify/ classify/
COPY emit/ emit/
COPY tools/nfa_verify tools/nfa_verify/
COPY scripts/ scripts/
COPY traces/ traces/

# Copy cargo registry from builder for offline rebuilds
COPY --from=builder /usr/local/cargo/registry /usr/local/cargo/registry

RUN chmod +x /app/nfa_verify /app/scripts/rebuild.sh
