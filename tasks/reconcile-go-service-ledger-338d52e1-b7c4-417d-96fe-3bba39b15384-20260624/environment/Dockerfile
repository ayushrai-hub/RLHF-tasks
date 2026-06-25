FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app

ENV GOTOOLCHAIN=local \
    CGO_ENABLED=0 \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        make \
        procps \
        python-is-python3 \
        python3 \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv \
    && python -m pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY app/ /app/

RUN go build ./...
