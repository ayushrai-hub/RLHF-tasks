FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/verify-venv \
    && /opt/verify-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && ln -sf /opt/verify-venv/bin/python /usr/local/bin/python \
    && ln -sf /opt/verify-venv/bin/pytest /usr/local/bin/pytest

ENV PATH="/opt/verify-venv/bin:${PATH}"

WORKDIR /app

COPY raw-events/ /app/raw-events/
COPY prior-ledger/ /app/prior-ledger/
COPY catalog/ /tmp/catalog/
COPY docs/ /app/docs/

RUN mkdir -p /app/catalog /app/output \
    && sqlite3 /app/catalog/meter_catalog.db < /tmp/catalog/schema.sql \
    && sqlite3 /app/catalog/meter_catalog.db < /tmp/catalog/seed.sql \
    && rm -rf /tmp/catalog
