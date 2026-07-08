FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac
ENV PATH="/usr/local/go/bin:${PATH}"

# tmux and asciinema support the interactive shell environment. Python is used
# by bundled helper scripts and by the test runner. Runtime has no internet.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip tmux asciinema \
    && rm -rf /var/lib/apt/lists/*
RUN ln -sf /usr/local/go/bin/go /usr/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/bin/gofmt

# Test dependency, pinned and installed at build time.
RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.2.0

# Pre-compile the Go standard library so builds are fast. The toolchain stays
# in the image because the program is rebuilt at runtime.
RUN go build std

WORKDIR /app
COPY task_file/ ./

# Keep the container alive for the interactive shell.
CMD ["sleep", "infinity"]
