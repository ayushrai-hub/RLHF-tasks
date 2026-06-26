FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS gobuild

WORKDIR /app
COPY . /app/environment

RUN mkdir -p /app/bin /app/output/stage /app/output/harness \
    && chmod +x /app/environment/scripts/*.sh \
    && /app/environment/scripts/build.sh

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
        python3-venv=3.11.2-1+b1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier \
    && /opt/verifier/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY --from=gobuild /usr/local/go /usr/local/go
COPY --from=gobuild /app/environment /app/environment
COPY --from=gobuild /app/bin /app/bin
COPY --from=gobuild /app/output /app/output

ENV PATH=/usr/local/go/bin:/opt/verifier/bin:${PATH}
ENV GOROOT=/usr/local/go

WORKDIR /app
