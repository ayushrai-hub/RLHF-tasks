FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932

# Headless agent harnesses (e.g. terminus-2/tmux) expect tmux, TERM, and a socket dir.
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends golang-go=2:1.22~2build1 python3=3.12.3-0ubuntu2.1 \
    ncurses-term=6.4+20240113-1ubuntu2 \
    ca-certificates=20240203 \
    openssl=3.0.13-0ubuntu3.11 \
    python3-pip=24.0+dfsg-1ubuntu1.3 \
    python3-venv=3.12.3-0ubuntu2.1 \
    tmux=3.4-1ubuntu0.1 \
    asciinema=2.4.0-1 \
    curl=8.5.0-2ubuntu10.9 \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

# terminal-bench:dockerfile-uv-offline-verifier
COPY runtime/tmux.conf /etc/tmux.conf
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5
RUN /opt/verifier-venv/bin/pytest --version
ENV PATH="/opt/verifier-venv/bin:/usr/bin:${PATH}"
ENV GOCACHE=/tmp/gocache
ENV GOMODCACHE=/tmp/gomodcache

COPY . /app/environment

RUN cd /app/environment \
 && go mod tidy \
 && go build -o /app/bin/verify-transfer-runs ./cmd/verify-transfer-runs \
 && chmod +x /app/environment/tools/verify-transfer-runs \
 && mkdir -p /app/data /app/output /app/state \
 && ln -sf /app/environment/data/fixtures /app/data/fixtures \
 && printf '%s\n' '{"fixture_label":"pack_k3","reader_epoch":"stale99","observed_bytes":500}' > /app/state/resume.offset

WORKDIR /app
