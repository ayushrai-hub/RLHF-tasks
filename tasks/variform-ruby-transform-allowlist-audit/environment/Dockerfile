# The agent surface is Ruby, but the sanctioned base-image allow list has no Ruby
# image; the canonical-image check requires this exact ECR-mirrored Python digest.
# Ruby runs the audited library and is installed from apt below; Python only hosts
# the pytest verifier venv. This dual-runtime layout is the documented justification
# for a Python base on a Ruby task.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      patch \
      ca-certificates \
      jq \
      tmux \
      asciinema \
      ruby \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt

WORKDIR /app/environment

COPY . /app/environment/

WORKDIR /app/environment
