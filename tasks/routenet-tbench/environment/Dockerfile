FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV PGDATA=/var/lib/postgresql/data
ENV PG_USER=trainer
ENV PG_PASSWORD=trainer
ENV PG_DB=routenet
ENV PG_HOST=127.0.0.1
ENV PG_PORT=5432

RUN echo '#!/bin/sh\nexit 0' > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema=2.2.0-1 \
        ca-certificates=20230311+deb12u1 \
        postgresql=15+248+deb12u1 \
        postgresql-client=15+248+deb12u1 \
        python3=3.11.2-1+b1 \
        python3-pip=23.0.1+dfsg-1 \
        python3-venv=3.11.2-1+b1 \
        sudo=1.9.13p3-1+deb12u4 \
        tmux=3.3a-3 \
    && rm -f /usr/sbin/policy-rc.d \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv

ENV PATH=/opt/verifier-venv/bin:${PATH}

WORKDIR /app

COPY requirements.lock ./
RUN /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes --no-deps -r requirements.lock

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund \
    && npm cache clean --force

COPY src/ src/
COPY scripts/ scripts/
COPY docs/ docs/
COPY data/ data/
COPY config/ config/
COPY README.md README.md
COPY .nvmrc .nvmrc

RUN chmod +x /app/scripts/start-system.sh \
    && mkdir -p /app/output \
    && install -d -o postgres -g postgres -m 0700 /var/lib/postgresql/data

ENV PATH=/usr/lib/postgresql/15/bin:${PATH}

CMD ["bash"]
