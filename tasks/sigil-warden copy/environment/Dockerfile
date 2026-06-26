FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

# Agent runtime (tmux, asciinema) plus a Python interpreter for the verifier.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Verifier dependencies, isolated in a venv so the test runner finds them on PATH.
ENV PATH=/opt/venv/bin:$PATH
RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir \
        pytest==8.3.4 \
        pytest-json-ctrf==0.5.2

# Keep the Go build hermetic and offline at agent/verifier time.
ENV GOTOOLCHAIN=local \
    GOFLAGS=-mod=mod

WORKDIR /app

# Agent-visible files only. Never copy solution/ or tests/.
COPY app/ /app/

LABEL org.opencontainers.image.title="sigil-warden" \
      org.opencontainers.image.description="Capability-token toolkit environment"
