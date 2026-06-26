FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux asciinema \
    r-base r-base-dev gfortran \
    libcurl4-openssl-dev libssl-dev libxml2-dev libicu-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "options(repos = 'https://packagemanager.posit.co/cran/__linux__/bookworm/2024-12-01'); \
    pkgs <- c('jsonlite', 'readr', 'dplyr', 'tidyr', 'stringr', 'glmnet', 'survey', 'Matrix'); \
    install.packages(pkgs, Ncpus = 2); \
    missing <- pkgs[!pkgs %in% rownames(installed.packages())]; \
    if (length(missing) > 0L) { message('R PACKAGES FAILED TO INSTALL: ', paste(missing, collapse = ', ')); quit(status = 1L) }"

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

COPY renv.lock /home/renv.lock
COPY SCHEMA.md /home/SCHEMA.md
COPY helpers/ /home/helpers/
COPY data/ /home/data/

RUN mkdir -p /home/output
WORKDIR /home
