FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS builder
WORKDIR /build
ENV GOTOOLCHAIN=local CGO_ENABLED=0
COPY go.mod ./
COPY src/ ./src/
# Smoke-compile the shipped sources at image build time.
RUN go build -o /tmp/smoke ./src

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
           tmux asciinema \
    && rm -rf /var/lib/apt/lists/*
# The bookworm apt repos do not carry a recent Go; reuse the builder toolchain.
COPY --from=builder /usr/local/go /usr/local/go
# Make the agent's login shell see `go`.
RUN echo 'export PATH=/usr/local/go/bin:$PATH' > /etc/profile.d/go.sh
ENV PATH=/usr/local/go/bin:$PATH
ENV GOROOT=/usr/local/go
ENV GOTOOLCHAIN=local
ENV GOCACHE=/tmp/go-build
ENV GOPATH=/tmp/go-path
RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY README.md /app/README.md
COPY go.mod /app/go.mod
COPY src/ /app/src/
COPY docs/ /app/docs/
COPY examples/ /app/examples/
