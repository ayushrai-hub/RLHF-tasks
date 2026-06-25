FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

COPY uv-bin/uv /usr/local/bin/uv
COPY uv-bin/uvx /usr/local/bin/uvx
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON_PREFERENCE=only-system \
    UV_NO_INDEX=1 \
    UV_FIND_LINKS=/app/verifier-wheels \
    UV_OFFLINE=1

COPY app/ /app/
