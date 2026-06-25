FROM golang:1.22-bookworm@sha256:3d699e4d15d0f8f13c9195c0632a16702b8cbdece2955af1c23b37ae5d55a253

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip tmux asciinema && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir \
    pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

ENV PATH="/usr/local/go/bin:${PATH}"
# Per Cloudflare RFC §4.2: CI override for window size
ENV RATELIMIT_WINDOW_MS=5000

COPY go.mod go.sum /app/
COPY cmd/ /app/cmd/
COPY internal/ /app/internal/
COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY scripts/ /app/scripts/
COPY benchmarks/ /app/benchmarks/
COPY README.md /app/

RUN go build -o bin/rate-limiter ./cmd/limiter
RUN mkdir -p /app/output
