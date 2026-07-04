FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app/environment

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/app/environment/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 \
      python3-venv \
      patch \
      jq \
      tmux \
      asciinema \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt

COPY go.mod .
COPY cmd/ cmd/
COPY src/ src/
COPY scripts/ scripts/
COPY testdata/ testdata/
