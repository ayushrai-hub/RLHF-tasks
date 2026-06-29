FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

# Headless agent harnesses (e.g. terminus-2/tmux) expect tmux, a sensible TERM, and a socket dir.
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV PATH="/usr/local/go/bin:/app/bin:${PATH}"
ENV GOTOOLCHAIN=local

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        ncurses-term \
        python3 \
        python3-pip \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pyyaml==6.0.2

COPY atlas-harden/go.mod atlas-harden/go.sum /app/atlas-harden/
RUN cd /app/atlas-harden && go mod download

COPY atlas-harden/ /app/atlas-harden/
COPY data/ /app/data/

RUN cd /app/atlas-harden && go build -o /app/bin/atlas-harden .

WORKDIR /app
