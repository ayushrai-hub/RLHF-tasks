FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
    pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app
COPY go.mod go.sum /app/
COPY cmd/ /app/cmd/
COPY pkg/ /app/pkg/
COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY scripts/ /app/scripts/

RUN go build -o /app/bin/transitivity-checker ./cmd/transitivity-checker
RUN mkdir -p /app/output
