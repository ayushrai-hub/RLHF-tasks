FROM public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    build-essential \
    ca-certificates \
    libicu-dev \
    libssl-dev \
    python3 \
    python3-pip \
    tmux \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
 && gem install rack --no-document --version 3.1.2 \
 && gem install rackup --no-document --version 2.1.0

ENV PATH="/usr/local/bundle/bin:${PATH}"

WORKDIR /app

RUN mkdir -p /app/output

COPY scripts/ /app/scripts/
COPY native/ /app/native/
COPY service/ /app/service/
COPY data/ /app/data/
COPY docs/ /app/docs/

RUN make -C /app/native
