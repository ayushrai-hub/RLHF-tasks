FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

WORKDIR /app

# Install system dependencies
RUN apt-get -o Acquire::Retries=3 update -qq \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        tmux \
        python3 python3-venv pkg-config bash coreutils procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (PIN VERSIONS!)
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

# Copy task files
COPY task_file /app/task_file

# Set up environment
ENV PATH="/opt/venv/bin:/usr/local/cargo/bin:${PATH}" CARGO_TERM_COLOR=never
WORKDIR /app/task_file
