FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV SHELL=/bin/bash

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    make \
    patch \
    asciinema \
    ca-certificates \
    ncurses-term \
    python3 \
    python3-venv \
    tmux \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/tmp/tmux /app/bin /app/output /app/work \
    && chmod 1777 /var/tmp/tmux \
    && command -v tmux >/dev/null \
    && command -v asciinema >/dev/null

COPY runtime/tmux.conf /etc/tmux.conf

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY Makefile /app/environment/Makefile
COPY tools/ /app/environment/tools/
COPY load_r8/ /app/environment/load_r8/
COPY scan_k3/ /app/environment/scan_k3/
COPY link_t2/ /app/environment/link_t2/
COPY trace/ /app/environment/trace/
COPY bridge/ /app/environment/bridge/
COPY fixtures/ /app/environment/fixtures/
COPY cfg/ /app/environment/cfg/
COPY misc/ /app/environment/misc/
COPY proto/ /app/environment/proto/
COPY tooling/ /app/tooling/

RUN chmod +x /app/tooling/run_h02.sh \
    && make -C /app/environment clean all
