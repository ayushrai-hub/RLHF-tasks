FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV TERM=xterm-256color \
    TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash golang-go make patch tmux asciinema \
    && mkdir -p /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN mkdir -p /app/output /app/work
COPY runtime/tmux.conf /etc/tmux.conf
COPY go.mod Makefile README.md /app/environment/
COPY cmd /app/environment/cmd
COPY cli /app/environment/cli
COPY packset /app/environment/packset
COPY auditx /app/environment/auditx
COPY internal /app/environment/internal
COPY scripts /app/environment/scripts
RUN chmod +x /app/environment/scripts/*.sh || true
