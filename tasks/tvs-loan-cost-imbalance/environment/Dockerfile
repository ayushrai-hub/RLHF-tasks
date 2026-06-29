# The canonical base-image registry has no R image, so the sanctioned Python
# base is used and R is added from apt below: it supplies the agent's R runtime
# and the Python venv that the verifier runs pytest in.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      asciinema \
      ca-certificates \
      libgomp1 \
      r-base \
      r-base-dev \
      tmux && \
    rm -rf /var/lib/apt/lists/*

RUN R -e "options(repos = 'https://packagemanager.posit.co/cran/__linux__/bookworm/2025-01-15'); \
    pkgs <- c('jsonlite', 'data.table', 'ranger'); \
    install.packages(pkgs, Ncpus = 2); \
    missing <- pkgs[!pkgs %in% rownames(installed.packages())]; \
    if (length(missing) > 0L) { message('R PACKAGES FAILED TO INSTALL: ', paste(missing, collapse = ', ')); quit(status = 1L) }"

RUN python3 -m venv /opt/test-venv

COPY requirements.lock /tmp/requirements.lock
RUN /opt/test-venv/bin/pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

WORKDIR /app
RUN mkdir -p /app/outputs

COPY data/ /app/data/
COPY contracts/ /app/contracts/
