# Single-stage canonical Go image: agents must compile and re-run make during debugging.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ARG TASK_IMAGE_REVISION=3

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PATH="/usr/local/go/bin:/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    GOTOOLCHAIN=local \
    GO111MODULE=on \
    CGO_ENABLED=0 \
    GOCACHE=/tmp/go-cache \
    GOPATH=/tmp/go \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        make \
        python-is-python3 \
        python3 \
        python3-pip \
        tmux \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/* /root/.cache

COPY requirements.lock /opt/verifier/requirements.lock
COPY wheels/ /opt/verifier/wheels/

RUN test -n "$(ls -A /opt/verifier/wheels/*.whl 2>/dev/null)"

WORKDIR /app

COPY go.mod Makefile /app/
COPY docker_network_connectivity_debugger_docs/ /app/docs/
COPY docker_network_connectivity_debugger_data/ /app/data/
COPY docker_network_connectivity_debugger_cmd/ /app/cmd/
COPY docker_network_connectivity_debugger_internal/ /app/internal/

RUN mkdir -p /app/build
