FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOTOOLCHAIN=local

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    ca-certificates \
    make \
    python3 \
    python3-pip \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir --require-hashes --no-deps --requirement=/tmp/requirements.txt

COPY task_file/src/ /app/src/
COPY task_file/docs/ /app/docs/
COPY task_file/Makefile /app/Makefile
COPY task_file/bin/ /app/bin/

WORKDIR /app
