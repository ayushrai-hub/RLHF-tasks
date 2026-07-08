# Go build plus verifier Python stack. Agent must compile columnar-validator at runtime.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive
ENV GOTOOLCHAIN=local
ENV GO111MODULE=on
ENV CGO_ENABLED=0

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        make \
        python3 \
        python3-pip \
        tmux \
 && python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        pyyaml==6.0.2 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY go.mod /app/
RUN go mod download

COPY Makefile /app/
COPY spec /app/spec
COPY rules /app/rules
COPY codec /app/codec
COPY writer /app/writer
COPY validator /app/validator
COPY fixtures /app/fixtures

RUN mkdir -p /app/bin /app/output
