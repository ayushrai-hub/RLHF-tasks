FROM public.ecr.aws/docker/library/debian@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV SHELL=/bin/bash

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    make=4.3-4.1 \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    coreutils=9.1-1 \
    ncurses-term=6.4-4 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && command -v tmux >/dev/null \
    && command -v asciinema >/dev/null \
    && command -v make >/dev/null \
    && command -v sha256sum >/dev/null

COPY runtime/tmux.conf /etc/tmux.conf

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY Makefile /app/environment/Makefile
COPY d0 /app/environment/d0
COPY lib /app/environment/lib
COPY tools /app/environment/tools
COPY fixtures /app/environment/fixtures
COPY actors /app/environment/actors
COPY q2_auth /app/environment/q2_auth
COPY q3_nnp /app/environment/q3_nnp
COPY q4_core /app/environment/q4_core
COPY q5_stage /app/environment/q5_stage
COPY q6_recover /app/environment/q6_recover
COPY q7_launch /app/environment/q7_launch

RUN mkdir -p /app/output /app/work \
    && make -C /app/environment all \
    && chmod -R a+w /app/environment \
    && chmod 1777 /app/output /app/work

ENV PATH="/app/environment/d0:/app/environment/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
