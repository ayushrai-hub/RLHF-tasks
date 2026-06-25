# syntax=docker/dockerfile:1.7
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS gotoolchain

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY --from=gotoolchain /usr/local/go /usr/local/go
RUN ln -s /usr/local/go/bin/go    /usr/local/bin/go \
 && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt
ENV GOPATH="/root/go" \
    GOCACHE="/root/.cache/go-build" \
    GOMODCACHE="/root/go/pkg/mod" \
    GOFLAGS="-mod=mod"

COPY go.mod go.sum ./
RUN go mod download

COPY . /app
RUN python /app/tools/gen_fixtures.py --out /app/testdata
