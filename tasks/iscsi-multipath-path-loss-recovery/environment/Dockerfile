FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932

# Headless agent harnesses (e.g. terminus-2/tmux) expect tmux, TERM, and a socket dir.
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ncurses-term=6.4+20240113-1ubuntu2 \
    python3=3.12.3-0ubuntu2.1 \
    ca-certificates=20240203 \
    golang-go=2:1.22~2build1 \
    python3-pip=24.0+dfsg-1ubuntu1.3 \
    python3-venv=3.12.3-0ubuntu2.1 \
    tmux=3.4-1ubuntu0.1 \
    asciinema=2.4.0-1 \
&& mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

# terminal-bench:dockerfile-uv-offline-verifier
COPY runtime/tmux.conf /etc/tmux.conf
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/python -m pip install pytest==8.4.1 pytest-json-ctrf==0.3.5
ENV PATH="/opt/verifier-venv/bin:/usr/bin:${PATH}"

COPY . /app/environment

RUN cd /app/environment \
 && go build -o /app/bin/pathfb-sweep ./cmd/pathfb_sweep \
 && mkdir -p /app/output /app/data /app/var/failback_journal \
 && ln -sf /app/environment/data/scenarios /app/data/scenarios

WORKDIR /app
