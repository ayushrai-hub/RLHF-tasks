# Digest-pinned canonical Rust base image (matches the sanctioned rust:1.85-slim).
# Justification: there is no Rust image in the t-bench canonical registry yet.
FROM rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

# build-essential provides the C linker cargo needs to compile the crate at
# verification time; python3/pip host the pytest verifier layer so tests never
# have to download anything at run time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3 \
    python3-pip \
    tmux \
    asciinema \
    && rm -rf /var/lib/apt/lists/*

# Pre-install the test dependencies (pytest + CTRF reporter) from a hash-pinned
# lockfile so the verifier runs fully offline.
COPY requirements.lock /tmp/requirements.lock
RUN pip3 install --break-system-packages --require-hashes --no-deps -r /tmp/requirements.lock

WORKDIR /app

# Copy only the application sources (tests and solution are mounted at verify time).
COPY app/Cargo.toml app/Cargo.lock /app/
COPY app/src /app/src
