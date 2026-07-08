FROM --platform=linux/amd64 public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir \
        pytest==9.0.3 \
        pytest-json-ctrf==0.5.0

RUN ln -s /usr/local/go/bin/go /usr/bin/go || true

RUN mkdir -p /opt/verifier-scripts

COPY scripts/verifier-rebuild.sh /opt/verifier-scripts/rebuild-tool
RUN chmod +x /opt/verifier-scripts/rebuild-tool

ENV PATH="/opt/verifier-scripts:${PATH}"
ENV CGO_ENABLED=0

WORKDIR /app

COPY go.mod ./
COPY cmd/ cmd/
COPY internal/ internal/
COPY docs/ docs/
COPY data/ data/

RUN go build -o /app/claim-weaver ./cmd/claim-weaver \
    && mkdir -p /app/output
