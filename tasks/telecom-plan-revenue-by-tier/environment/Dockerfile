FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update && apt-get install -y --no-install-recommends \
        r-base-core \
        r-cran-readr \
        r-cran-dplyr \
        r-cran-tidyr \
        r-cran-jsonlite \
        r-cran-stringr \
        r-cran-lubridate \
        tmux \
        asciinema \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

WORKDIR /app

COPY data/ /app/data/
COPY docs/ /app/docs/
COPY R/ /app/R/
COPY DESCRIPTION /app/DESCRIPTION
COPY analysis.R /app/analysis.R
