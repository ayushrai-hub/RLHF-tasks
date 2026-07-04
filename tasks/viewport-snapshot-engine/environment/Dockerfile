# Sanctioned canonical reference required by CI: the public.ecr.aws mirror of
# python:3.13-slim-bookworm at its canonical multi-arch manifest digest (resolves
# on the amd64 CI builder as well as arm64 dev machines).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# OS packages (least volatile layer). tmux + asciinema are required by the
# offline terminal-recording verifier; ca-certificates is general hygiene.
# Versions are pinned to those shipped by the digest-pinned bookworm base, in a
# single transaction, no recommends, with the lists cleaned up in the same layer.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tmux=3.3a-3 \
      asciinema=2.2.0-1 \
      ca-certificates=20230311+deb12u1 \
 && rm -rf /var/lib/apt/lists/*

# Build the offline verifier virtualenv at image-build time (the only stage with
# network). With allow_internet=false the verifier phase has NO network, so the
# test runner installs nothing and just activates this venv. These are generic
# test-harness tools (pytest + a CTRF reporter) that reveal nothing about
# grading; the real test logic lives in /tests, mounted only at verify time and
# never present in this image.
COPY requirements.lock /tmp/requirements.lock
RUN python -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
 && rm -f /tmp/requirements.lock

WORKDIR /app

# The graded task is fully self-contained: the agent writes /app/viewport.py from
# the instructions using only the Python standard library. No project source is
# shipped in the image.
