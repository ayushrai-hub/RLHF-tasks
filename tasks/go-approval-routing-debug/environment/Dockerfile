# Sanctioned final runtime base (python:*@sha256:); Go is installed from the
# official pinned tarball below rather than using the golang:* image, which is a
# non-sanctioned custom final base.
FROM python:3.12-bookworm@sha256:e1d7ed147cb68be5a443a82377dd944f4f6fb529a5293cf11a1c482034abed2e

# tmux + asciinema are required by the harness to drive the agent terminal.
# build-essential (gcc) is needed so the Go race detector can link at
# verification time. All deps are installed here at build time because the
# runtime phase has no internet.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

# Install Go from the official tarball, pinned by SHA-256 (build phase only;
# no internet at runtime).
ENV GO_VERSION=1.21.13
ENV GO_SHA256=502fc16d5910562461e6a6631fb6377de2322aad7304bf2bcd23500ba9dab4a7
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tar.gz \
    && echo "${GO_SHA256}  /tmp/go.tar.gz" | sha256sum -c - \
    && tar -C /usr/local -xzf /tmp/go.tar.gz \
    && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH=/root/go GOTOOLCHAIN=local

# The harness drives the agent through a tmux *login* shell, which sources
# /etc/profile and can reset PATH — clobbering the ENV PATH above so `go` is not
# found and agents waste steps hunting for the toolchain. Make `go`/`gofmt`
# reachable two ways that survive a PATH reset: symlink them into /usr/local/bin
# (always on the default PATH) and drop a profile.d snippet that re-exports PATH.
RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt \
    && printf 'export PATH=/usr/local/go/bin:$PATH\nexport GOPATH=/root/go\nexport GOTOOLCHAIN=local\n' \
        > /etc/profile.d/go.sh

# Test dependencies, pinned and pre-installed (no network at runtime).
RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.2.0 \
    requests==2.32.3

# Pre-compile the Go standard library (incl. the race runtime) for faster builds.
RUN CGO_ENABLED=1 go build -race std || go build std

WORKDIR /app
COPY task_file/ ./

# Verify the source compiles and warm the build cache.
WORKDIR /app/src
RUN go build -o /dev/null .

WORKDIR /app

# Keep the container alive so the harness can attach a tmux session.
CMD ["sleep", "infinity"]
