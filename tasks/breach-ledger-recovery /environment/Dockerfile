FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    --allow-downgrades \
    python3 \
    python3-pip \
    sqlite3 \
    ca-certificates \
    tmux \
    asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY go.mod /app/go.mod
COPY cmd /app/cmd
COPY internal /app/internal
COPY docs /app/docs
COPY fixtures /app/fixtures
COPY tools /app/tools

RUN base64 -d /app/fixtures/omega/audit/frames.bin.b64 > /app/fixtures/omega/audit/frames.bin \
    && rm /app/fixtures/omega/audit/frames.bin.b64 \
    && base64 -d /app/fixtures/omega/logs/auth.log.1.gz.b64 > /app/fixtures/omega/logs/auth.log.1.gz \
    && rm /app/fixtures/omega/logs/auth.log.1.gz.b64 \
    && base64 -d /app/fixtures/omega/archives/staged.zip.b64 > /app/fixtures/omega/archives/staged.zip \
    && rm /app/fixtures/omega/archives/staged.zip.b64 \
    && sqlite3 /app/fixtures/omega/deleted/deleted.sqlite < /app/fixtures/omega/deleted/deleted.sql \
    && rm /app/fixtures/omega/deleted/deleted.sql

RUN go build -o /app/bin/breach-ledger /app/cmd/breach-ledger

RUN mkdir -p /app/output && chmod 1777 /app/output

CMD ["/bin/bash"]
