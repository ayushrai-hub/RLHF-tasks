FROM python:3.12-slim@sha256:0c61694d5a33df8a5b454feaa9b268571e45e6027a1115c212d8c0e6264a9b5e

RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.3.4 pytest-json-ctrf==0.3.5

WORKDIR /app
COPY app/ /app/
