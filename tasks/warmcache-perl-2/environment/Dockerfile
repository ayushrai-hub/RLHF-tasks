FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
LABEL org.opencontainers.image.title="warmcache-perl-2"

# Perl (the task substrate) plus the terminal-recording utilities the verifier needs.
# MIME::Base64 is part of the Perl core, and the POSIX coreutils (cksum/base64/sort/join/cut)
# ship in the base image, so no extra libraries are required. The canonical python ECR base
# with the toolchain layered on top needs no non-canonical-image justification.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        perl \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

# Verifier dependencies are baked in at build time because the task runs offline
# (allow_internet = false). Fully hash-pinned via a lockfile so transitive deps freeze.
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

WORKDIR /app
RUN mkdir -p /app/out
COPY app/ /app/
