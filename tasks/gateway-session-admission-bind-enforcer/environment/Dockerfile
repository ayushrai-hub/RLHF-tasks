FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

# Make Go available in login and non-login agent shells (parity with verifier).
RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt \
    && printf '%s\n' 'export PATH="/usr/local/go/bin:${PATH}"' \
        > /etc/profile.d/go-toolchain.sh \
    && chmod 644 /etc/profile.d/go-toolchain.sh

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        build-essential \
        ca-certificates \
        libssl-dev \
        pkg-config \
        python3 \
        python3-pip \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

ENV PATH="/usr/local/go/bin:/opt/verifier-venv/bin:${PATH}"

COPY go.mod main.go /app/environment/
COPY docs /app/environment/docs/
COPY config /app/environment/config/
COPY rate /app/environment/rate/
COPY balance /app/environment/balance/
COPY session /app/environment/session/

RUN ln -s /app/environment/docs /app/docs

RUN mkdir -p /app/sessions
