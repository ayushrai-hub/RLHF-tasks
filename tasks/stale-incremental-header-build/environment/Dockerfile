FROM public.ecr.aws/docker/library/debian@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    build-essential \
    ca-certificates \
    cmake \
    gcc \
    ncurses-term \
    python3 \
    python3-venv \
    tmux \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/tmp/tmux /app/output \
    && chmod 1777 /var/tmp/tmux

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY runtime/tmux.conf /etc/tmux.conf
COPY . /app/environment

RUN cmake -S /app/environment -B /app/environment/_build \
    && cmake --build /app/environment/_build --target bld_host trace_host
