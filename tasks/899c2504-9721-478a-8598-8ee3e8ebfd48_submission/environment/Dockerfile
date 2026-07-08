FROM python:3.13-slim@sha256:d49c1ff87eb98eac346fc250f52925f726eb913c43a92854246dd03c9692ad67

WORKDIR /app

ENV TMUX_TMPDIR=/tmp/.harbor-tmux \
    TERM=xterm-256color \
    SHELL=/bin/bash

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash=5.2.37-2+b8 \
    coreutils=9.7-3 \
    tmux=3.5a-3 \
    asciinema=2.4.0-1 \
    && mkdir -p /tmp/.harbor-tmux \
    && chmod 1777 /tmp/.harbor-tmux \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY tools /app/environment/tools
COPY src /app/environment/src
COPY config /app/environment/config
COPY data /app/environment/data
COPY docs /app/environment/docs
COPY scripts /app/environment/scripts

RUN chmod +x /app/environment/tools/run_pipeline.sh /app/environment/scripts/reset_workspace.sh
