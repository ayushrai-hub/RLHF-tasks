FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends python3=3.11.2-1+b1 python3-pip=23.0.1+dfsg-1 python3-venv=3.11.2-1+b1 \
    build-essential=12.9 \
    make=4.3-4.1 \
    libjsoncpp-dev=1.9.5-4 \
    libssl-dev=3.0.20-1~deb12u2 \
    ca-certificates=20230311+deb12u1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    curl=7.88.1-10+deb12u14 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://astral.sh/uv/0.9.5/install.sh \
    -o /tmp/uv-installer.sh \
    && sh /tmp/uv-installer.sh \
    && rm /tmp/uv-installer.sh

ENV PATH="/root/.local/bin:${PATH}"

RUN uv python install 3.13 \
    && uvx -p 3.13 -w pytest==8.4.1 -w pytest-json-ctrf==0.3.5 -w requests==2.32.3 pytest --version

RUN python3 -m venv /opt/sidecar-venv \
    && /opt/sidecar-venv/bin/pip install --no-cache-dir polars==1.12.0

ENV PATH="/opt/sidecar-venv/bin:/opt/verifier-venv/bin:${PATH}"

WORKDIR /app

RUN mkdir -p /app/bin /app/output /app/docs

COPY . /app/environment/

RUN python3 /app/environment/data/generate_dossier.py \
    && cd /app/environment \
    && make install \
    && chmod +x /app/environment/ci/start-score-server.sh \
        /app/environment/ci/check-paths.sh \
        /app/environment/scripts/run-batch-audit.sh \
    && /app/environment/ci/check-paths.sh
