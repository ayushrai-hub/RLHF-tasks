FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.source="s-project"
LABEL org.opencontainers.image.revision="local"
LABEL org.opencontainers.image.created="2026-06-26"
LABEL org.opencontainers.image.version="1.0"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update     && apt-get install -y --no-install-recommends         asciinema         ca-certificates         python3         python3-pytest         tmux     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/go.mod /app/go.mod
COPY --chmod=0755 app/bin/local-retention-reconciler.go /app/bin/local-retention-reconciler.go
COPY app/src/ /app/src/
COPY app/docs/ /app/docs/
COPY app/config/ /app/config/
COPY app/manifests/ /app/manifests/
COPY app/out/ /app/out/

ENV PATH="/usr/local/go/bin:${PATH}"
ENV TERM=xterm-256color
CMD ["bash"]
