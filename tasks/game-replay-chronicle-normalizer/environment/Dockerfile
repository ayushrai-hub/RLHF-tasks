FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        gzip \
        python3 \
        python3-pip \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==9.0.3 \
        pytest-json-ctrf==0.5.0

RUN mkdir -p /opt/verifier-scripts /app/bin
COPY scripts/rebuild-game-replay-chronicle-normalizer /opt/verifier-scripts/rebuild-game-replay-chronicle-normalizer
RUN chmod +x /opt/verifier-scripts/rebuild-game-replay-chronicle-normalizer

WORKDIR /app

COPY go.mod go.sum ./
COPY vendor ./vendor
COPY cmd/ ./cmd/
COPY internal/ ./internal/
COPY docs/ ./docs/
COPY Makefile ./
RUN go build -mod=vendor -o /app/bin/replay-chronicle ./cmd/replay-chronicle

COPY scripts/ ./scripts/
RUN chmod +x /app/scripts/replay-pack.sh /app/scripts/replay-unpack.sh

ENV PATH="/opt/verifier-scripts:/app/bin:${PATH}"
