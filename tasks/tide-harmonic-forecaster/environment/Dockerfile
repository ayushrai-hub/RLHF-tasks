# Canonical Go runtime base image for offline task execution.
# Matches the approved Go base: public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="tide-harmonic-forecaster"
LABEL org.opencontainers.image.description="Offline Go harmonic tide forecasting task"

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==8.4.1

RUN ln -s /usr/local/go/bin/go /usr/local/bin/go \
    && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt \
    && printf 'export PATH="/usr/local/go/bin:/go/bin:$PATH"\n' > /etc/profile.d/go.sh

WORKDIR /app
COPY task_file/go.mod /app/go.mod
COPY task_file/main.go /app/main.go
COPY task_file/model /app/model
COPY task_file/forecast /app/forecast
COPY task_file/planner /app/planner
COPY task_file/report /app/report
COPY task_file/model.json /app/model.json
COPY task_file/gauges.jsonl /app/gauges.jsonl
RUN mkdir -p /app/output
RUN go build -o /tmp/tide-harmonic-warmup . \
    && rm -f /tmp/tide-harmonic-warmup

CMD ["sleep", "infinity"]
