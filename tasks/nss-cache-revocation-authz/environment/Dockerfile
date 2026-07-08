FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV TERM=xterm-256color
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV PATH="/opt/verifier-venv/bin:${PATH}"
ENV GOCACHE=/go/cache
ENV GOMODCACHE=/go/pkg/mod

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates make patch python-is-python3 python3 python3-pip python3-venv tmux asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 \
    && mkdir -p /var/tmp/tmux /go/cache /go/pkg/mod \
    && chmod 1777 /var/tmp/tmux \
    && asciinema --version >/dev/null

RUN mkdir -p /app/output /app/work /app/environment
COPY go.mod Makefile /app/environment/
COPY cmd /app/environment/cmd
COPY internal /app/environment/internal
COPY docs /app/environment/docs
COPY fixtures /app/environment/fixtures
COPY scripts /app/environment/scripts
COPY runtime/tmux.conf /tmp/tmux.conf

RUN sed -i 's/\r$//' /tmp/tmux.conf \
    && mv /tmp/tmux.conf /etc/tmux.conf \
    && chmod +x /app/environment/scripts/run_case.sh \
    && cd /app/environment && go build -trimpath -o bin/authzctl ./cmd/authzctl
