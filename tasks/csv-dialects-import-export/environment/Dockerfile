# Python 3.13 + PHP 8.2
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        php8.2-cli \
        php8.2-mbstring \
        php8.2-xml \
        php8.2-curl \
        composer \
        unzip \
        git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY repo/ /app/

RUN cd /app && composer install --no-dev --no-interaction --no-progress --ignore-platform-req=ext-xdebug 2>&1

WORKDIR /app
