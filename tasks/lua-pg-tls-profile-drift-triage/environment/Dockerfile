# python:3.13-slim-bookworm — Lua PostgreSQL TLS profile drift triage
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    gawk \
    tmux \
    asciinema \
    lua5.4 \
    make \
    postgresql \
    postgresql-client \
    python3-yaml \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock
RUN rm -f /tmp/requirements.lock

ENV PATH="/opt/verifier-venv/bin:${PATH}"

RUN service postgresql start \
    && runuser -u postgres -- psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" \
    && service postgresql stop

WORKDIR /app

RUN mkdir -p /app/out /app/bin /app/var/tls/stage

COPY . /app/environment/

RUN chmod +x /app/environment/cli/ingressctl \
    /app/environment/ci/*.sh \
    && bash /app/environment/ci/install_cli.sh \
    && cp -r /app/environment/docs /app/docs \
    && /app/environment/ci/path_check.sh
