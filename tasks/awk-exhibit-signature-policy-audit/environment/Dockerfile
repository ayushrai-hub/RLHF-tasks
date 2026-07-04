FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive

# apt package versions are intentionally not pinned. The base image is pinned by
# digest and every non-apt dependency is pinned by hash in requirements.lock.
# Pinning exact Debian point versions makes the build fail once those versions
# rotate out of the live bookworm mirror, so the package names install whatever
# the mirror currently serves.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        gawk \
        jq \
        openssl \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        tmux \
    && python3 -m venv /opt/verifier \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN /opt/verifier/bin/pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

WORKDIR /app

COPY app/ /app/

RUN chmod +x /app/bin/audit.sh /app/bin/start_registry.sh /app/bin/trust_registry.py \
    && install -d -m 0755 /app/output /app/runtime
