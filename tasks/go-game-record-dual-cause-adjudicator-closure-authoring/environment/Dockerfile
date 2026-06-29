FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS go-toolchain
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

COPY --from=go-toolchain /usr/local/go /usr/local/go
ENV GOPATH=/go
ENV PATH="/usr/local/go/bin:/go/bin:${PATH}"
RUN mkdir -p /go

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 \
    && ln -sf /usr/local/go/bin/go /usr/local/bin/go

WORKDIR /app

COPY go.mod ./
COPY cmd/ ./cmd/
COPY internal/ ./internal/
COPY docs/ ./docs/
COPY u/ ./u/
COPY r/ ./r/
COPY j/ ./j/
COPY tools/ ./tools/

RUN chmod +x tools/run_public_workflow.sh
