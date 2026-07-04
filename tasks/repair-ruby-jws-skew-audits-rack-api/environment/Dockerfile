# StampGate classroom API and JWS audit fixtures.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    ruby \
    ruby-sqlite3 \
    libsqlite3-dev \
    libssl-dev \
    curl \
    sqlite3 \
    ca-certificates \
    tmux \
    asciinema \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN pip3 install --no-cache-dir --break-system-packages \
    --require-hashes --no-deps -r /tmp/requirements.lock

COPY workspace/ /workspace/
COPY generate_stampgate.py /tmp/generate_stampgate.py

RUN python3 /tmp/generate_stampgate.py \
    && rm -rf /workspace/keys \
    && chmod +x /workspace/scripts/start-stampgate-api.sh \
    && chmod +x /workspace/stampgate-lib/bin/stampgate-audit \
    && chmod +x /workspace/stampgate-api/app.rb \
    && python3 -c "import importlib.metadata as m; m.version('pytest-json-ctrf')" \
    && rm -f /tmp/generate_stampgate.py

ENV RUBYLIB=/workspace/stampgate-lib/lib
