# Sanctioned base: the canonical python-slim ECR mirror; R is added via apt below (no canonical R base image exists).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      r-base-core \
      tmux asciinema procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      pytest==8.4.1 \
      pytest-json-ctrf==0.3.5

WORKDIR /app
RUN mkdir -p /app/environment/data /app/environment/outputs

COPY analysis.R /app/environment/analysis.R
COPY OUTPUT_CONTRACT.md /app/environment/OUTPUT_CONTRACT.md
COPY data/ /app/environment/data/
