FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux asciinema ca-certificates \
    python3-venv=3.11.2-1+b1 \
    r-base-core=4.2.2.20221110-2 \
    r-cran-nlme=3.1.162-1 \
    r-cran-jsonlite=1.8.4+dfsg-1 \
    r-cran-ggplot2=3.4.1+dfsg-1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN /usr/bin/python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt

ENV PATH="/opt/verifier-venv/bin:$PATH"
WORKDIR /app/environment

COPY data/ /app/environment/data/
COPY R/ /app/environment/R/
COPY analysis.R /app/environment/analysis.R
