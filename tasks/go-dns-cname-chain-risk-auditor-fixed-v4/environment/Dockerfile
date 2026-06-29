FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.source="s-project"
LABEL org.opencontainers.image.revision="local"
LABEL org.opencontainers.image.created="2026-06-27"
LABEL org.opencontainers.image.version="1.0"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

RUN apt-get update     && apt-get install -y --no-install-recommends         python3         python3-pytest         tmux         asciinema     && rm -rf /var/lib/apt/lists/*

COPY app/go.mod /app/go.mod
COPY app/bin/ /app/bin/
COPY app/cmd/ /app/cmd/
COPY app/config/ /app/config/
COPY app/docs/ /app/docs/
COPY app/fixtures/ /app/fixtures/

RUN chmod 0755 /app/bin/audit-cname-chains
