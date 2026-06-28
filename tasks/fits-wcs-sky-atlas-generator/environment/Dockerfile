FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

LABEL org.opencontainers.image.source="terminus/fits-wcs-sky-atlas-generator"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

ENV PATH="/opt/verifier-venv/bin:/opt/verifier-scripts:${PATH}"

COPY CMakeLists.txt /app/CMakeLists.txt
COPY include /app/include
COPY src /app/src
COPY config /app/config
COPY docs /app/docs
COPY scripts /app/scripts
COPY tools /app/tools

WORKDIR /app

RUN python3 /app/tools/gen_fixtures.py \
 && mkdir -p /app/bin /app/output /app/var /opt/verifier-fixtures \
 && cmake -S /app -B /app/build -G Ninja \
 && cmake --build /app/build \
 && cp /app/build/wcs-atlas /app/bin/wcs-atlas

RUN mkdir -p /opt/verifier-scripts \
 && cp /app/scripts/build.sh /opt/verifier-scripts/rebuild-wcs-atlas \
 && chmod +x /opt/verifier-scripts/rebuild-wcs-atlas /app/scripts/build.sh

WORKDIR /app
