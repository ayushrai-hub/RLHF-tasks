FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates coreutils patch python3 python3-venv python-is-python3 tmux asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/task-venv \
    && /opt/task-venv/bin/python -m pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 \
    && printf '%s\n' '#!/bin/sh' 'exec /opt/task-venv/bin/python "$@"' > /usr/local/bin/python \
    && chmod +x /usr/local/bin/python

ENV PATH="/opt/task-venv/bin:${PATH}"
WORKDIR /app
RUN mkdir -p /app/output /app/bin /app/work
COPY Cargo.toml Cargo.lock requirements.lock /app/environment/
COPY docs /app/environment/docs
COPY fixtures /app/environment/fixtures
COPY scripts /app/environment/scripts
COPY src /app/environment/src
RUN chmod +x /app/environment/scripts/*.sh
