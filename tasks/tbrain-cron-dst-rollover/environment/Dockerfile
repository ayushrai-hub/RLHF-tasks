FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        tmux \
        asciinema \
        util-linux \
        patch \
        git \
        ripgrep \
        ca-certificates \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Verifier-only Python dependencies, hash-locked and offline thereafter.
COPY requirements.lock /tmp/requirements.lock
RUN pip3 install --no-cache-dir --break-system-packages --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock

# Put the Go toolchain on the agent's login-shell PATH.
RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt

WORKDIR /app
COPY repo/ /app/

# Warm the build cache so the agent's post-edit rebuild is incremental.
ENV GOFLAGS=-mod=mod
RUN go build -o /app/dstcron ./cmd/dstcron && go vet ./... || true

# Initialize a git repo so agent edit/diff tooling works at runtime.
RUN git init -q \
    && git config user.email task@example.com \
    && git config user.name task \
    && git add -A \
    && git commit -q -m "initial task state"
