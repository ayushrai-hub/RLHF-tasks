FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        patch \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --prefer-binary \
    pytest==9.0.3 \
    pytest-json-ctrf==0.5.0 \
    cryptography==42.0.5 \
    pyyaml==6.0.2 \
    click==8.1.7

WORKDIR /app
COPY app/ /app/

ENV PYTHONPATH=/app

RUN mkdir -p /app/state /opt/verifier-fixtures/tb3 \
    && python3 /app/scripts/gen_verifier_fixtures.py \
    && rm -f /app/scripts/gen_verifier_fixtures.py

# Verifier tests and oracle solution are mounted at runtime — not baked into this image.
