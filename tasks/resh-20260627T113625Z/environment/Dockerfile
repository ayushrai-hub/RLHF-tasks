FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir \
        iniconfig==2.3.0 \
        packaging==26.2 \
        pluggy==1.6.0 \
        pygments==2.20.0 \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
    && python -m pytest --version
COPY app/ /app/
