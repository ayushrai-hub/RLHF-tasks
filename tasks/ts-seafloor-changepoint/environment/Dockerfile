# syntax=docker/dockerfile:1.4
FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-pip \
        python-is-python3 \
        sqlite3 \
        tmux \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --break-system-packages --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

WORKDIR /app

# Install Node deps (lockfile-first for reproducibility; better-sqlite3 needs native build)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files
COPY tsconfig.json ./
COPY src/ ./src/

# Copy static data assets and docs (database shipped compressed; expanded at build time)
COPY data/station_coords.json ./data/station_coords.json
COPY data/sensors.db.gz ./data/sensors.db.gz
COPY docs/ ./docs/

RUN gunzip -c /app/data/sensors.db.gz > /app/data/sensors.db && rm /app/data/sensors.db.gz
