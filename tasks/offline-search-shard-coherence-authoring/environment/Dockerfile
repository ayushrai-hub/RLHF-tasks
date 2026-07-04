FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

COPY requirements.lock /tmp/verifier-requirements.txt

# Harness roots: pytest==8.4.1 and pytest-json-ctrf==0.3.5.
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates python3 python3-pip python-is-python3 make tmux asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir --require-hashes \
        -r /tmp/verifier-requirements.txt \
    && rm /tmp/verifier-requirements.txt

WORKDIR /app

COPY go.mod /app/environment/go.mod
COPY cmd /app/environment/cmd
COPY internal /app/environment/internal
COPY configs /app/environment/configs
COPY data /app/environment/data
COPY state /app/environment/state
COPY docs /app/environment/docs
COPY scripts /app/environment/scripts
COPY README.md /app/environment/README.md

RUN chmod +x /app/environment/scripts/*.sh \
    && cd /app/environment \
    && go build -o /usr/local/bin/offline-search /app/environment/cmd/offline-search
