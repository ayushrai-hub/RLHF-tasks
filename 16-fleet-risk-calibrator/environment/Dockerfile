FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema=2.2.0-1 \
        ca-certificates=20230311+deb12u1 \
        python3-venv=3.11.2-1+b1 \
        tmux=3.3a-3 \
    && ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check \
        --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

ENV GOPROXY=off
ENV GOSUMDB=off
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /app

COPY app/ /app/
