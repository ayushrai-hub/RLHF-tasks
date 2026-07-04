FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    patch \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

ENV PATH="/opt/verifier-venv/bin:${PATH}"

COPY package.json package-lock.json /app/
RUN npm ci --omit=dev

COPY raft_mesh /app/raft_mesh
COPY consensus_lab /app/consensus_lab
COPY config /app/config
COPY docs /app/docs
COPY scenarios /app/scenarios
COPY tools /app/tools

RUN python3 /app/tools/materialize_wal.py \
    /app/scenarios/partition/wal_entries.jsonl \
    /app/scenarios/partition/wal_frames.bin

RUN mkdir -p /app/output
