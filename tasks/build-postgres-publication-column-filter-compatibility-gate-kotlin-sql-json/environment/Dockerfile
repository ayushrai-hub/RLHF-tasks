FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

LABEL org.opencontainers.image.source="internal-logical-replication-tooling" \
      org.opencontainers.image.revision="column-filter-gate" \
      org.opencontainers.image.created="2026-06-20T00:00:00Z" \
      org.opencontainers.image.version="2.0" \
      org.opencontainers.image.licenses="UNLICENSED"

WORKDIR /app

ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/jni

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        kotlin \
        libgoogle-gson-java \
        libxerial-sqlite-jdbc-java \
        openjdk-11-jdk-headless \
        python3 \
        python-is-python3 \
        python3-pip \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.lock

COPY --chmod=0755 app_entrypoint.py /app/app_entrypoint.py
COPY --chmod=0755 app/build.sh /app/build.sh
COPY --chmod=0755 scripts/ /app/scripts/
COPY src/ /app/src/
COPY input/ /app/input/
COPY sql/ /app/sql/
COPY docs/ /app/docs/
COPY examples/ /app/examples/
COPY README.md /app/README.md

RUN mkdir -p /app/build /app/data /app/out \
    && /app/build.sh
