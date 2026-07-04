# Base: the canonical Python slim image provides python3 for the pytest verifier;
# the Go toolchain is installed so the agent's Go solver compiles and runs fully offline.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates \
        tmux asciinema \
    && curl -fsSL --retry 3 --max-time 180 https://go.dev/dl/go1.22.10.linux-amd64.tar.gz -o /tmp/go.tgz \
    && echo "736ce492a19d756a92719a6121226087ccd91b652ed5caec40ad6dbfb2252092  /tmp/go.tgz" | sha256sum -c - \
    && tar -C /usr/local -xzf /tmp/go.tgz \
    && rm /tmp/go.tgz \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/go/bin:$PATH" \
    GOTOOLCHAIN=local \
    GOFLAGS=-mod=mod \
    GOPROXY=off \
    GOCACHE=/root/.cache/go-build

RUN python -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY task_file/ /app/task_file/
RUN mkdir -p /app/task_file/output_data

# Warm the Go build cache (std lib) so offline runtime builds are fast.
RUN cd /app/task_file/src && go build -o /tmp/warm . && rm -f /tmp/warm

WORKDIR /app
