FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV REBUILD=2026-06-28-v3
RUN dpkg --add-architecture amd64 \
    && apt-get update && apt-get install -y --no-install-recommends \
        wget \
        unzip \
        ca-certificates \
        libc6:amd64 \
        libstdc++6:amd64 \
        libssl3:amd64 \
        libicu72:amd64 \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

RUN wget -q -O /tmp/dafny.zip https://github.com/dafny-lang/dafny/releases/download/v4.9.0/dafny-4.9.0-x64-ubuntu-20.04.zip \
    && echo "b21575395f2fe3dbcaca09a8219fe29c99d248134e516e95dc3f0c3687d16c27  /tmp/dafny.zip" | sha256sum -c - \
    && unzip -q /tmp/dafny.zip -d /opt && rm /tmp/dafny.zip

ENV PATH="/opt/dafny:${PATH}"

RUN pip3 install --no-cache-dir pytest==8.2.0 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY solution.dfy /app/solution.dfy
COPY docs/ /app/docs/
COPY verify.sh /app/verify.sh
COPY run.sh /app/run.sh
