FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        python3 \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (PIN VERSIONS!)
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
    && ln -sf /opt/verifier-venv/bin/python /usr/local/bin/python

# Copy task files
COPY app/ /app/

# Set up environment
ENV PYTHONPATH=/app
ENV PATH="/opt/verifier-venv/bin:${PATH}"
ENV GOTOOLCHAIN=local
ENV GOFLAGS=-mod=mod
