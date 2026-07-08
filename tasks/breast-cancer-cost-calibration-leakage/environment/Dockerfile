FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      asciinema \
      ca-certificates \
      libgomp1 \
      libopenblas0-pthread \
      tmux && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

WORKDIR /app
RUN mkdir -p /app/data /app/outputs /app/contracts

COPY data/ /app/data/
COPY contracts/ /app/contracts/
COPY analysis.py /app/analysis.py
