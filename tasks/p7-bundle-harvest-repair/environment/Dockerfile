# syntax=docker/dockerfile:1

FROM public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    ca-certificates=20230311+deb12u1 \
    curl=7.88.1-10+deb12u14 \
    git=1:2.39.5-0+deb12u2 \
    libsqlite3-dev=3.40.1-2+deb12u2 \
    libyaml-dev=0.2.5-1 \
    pkg-config=1.8.1-1 \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
       pytest==8.4.1 pytest-json-ctrf==0.3.5 pytest-randomly==3.16.0

RUN ln -sf /opt/verifier-venv/bin/pytest /usr/local/bin/pytest

ENV PATH="/opt/verifier-venv/bin:${PATH}"

WORKDIR /app

COPY api /app/environment/api
COPY rb /app/environment/rb
COPY net /app/environment/net
COPY corpus /app/environment/corpus
COPY docs /app/environment/docs
COPY scripts /app/environment/scripts

RUN ln -sf /app/environment/rb /app/rb \
    && ln -sf /app/environment/net /app/net \
    && ln -sf /app/environment/corpus /app/corpus \
    && ln -sf /app/environment/docs /app/docs \
    && ln -sf /app/environment/scripts /app/scripts \
    && ln -sf /app/environment/api /app/api

RUN chmod +x /app/environment/scripts/*.sh /app/environment/rb/p7_pull/exe/p7_driver \
    && cd /app/environment/api/q9_host \
    && bundle config set --local path vendor/bundle \
    && bundle install --jobs 4 \
    && bundle exec rake db:setup \
    && cd /app/environment/rb/p7_pull \
    && bundle config set --local path vendor/bundle \
    && bundle install --jobs 4

RUN mkdir -p /app/output

CMD ["sleep", "infinity"]
