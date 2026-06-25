FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    cmake=3.25.1-1 \
    g++=4:12.2.0-3 \
    make=4.3-4.1 \
    ncurses-term=6.4-4 \
    ninja-build=1.11.1-2~deb12u1 \
    tmux=3.3a-3 \
    && mkdir -p /var/tmp/tmux /app/var/vlt_journal \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

COPY runtime/tmux.conf /etc/tmux.conf

RUN python -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY include /app/environment/include
COPY common /app/environment/common
COPY m02 /app/environment/m02
COPY r04 /app/environment/r04
COPY n09 /app/environment/n09
COPY q11 /app/environment/q11
COPY w33 /app/environment/w33
COPY persist /app/environment/persist
COPY runner/main.cpp /app/environment/runner/main.cpp
COPY fixtures /app/environment/fixtures
COPY docs /app/environment/docs
COPY CMakeLists.txt /app/environment/CMakeLists.txt

RUN mkdir -p /app/output /app/build \
    && cmake -S /app/environment -B /app/build -G Ninja \
    && ninja -C /app/build vlt_run
