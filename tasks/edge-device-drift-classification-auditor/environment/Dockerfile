# Pinned public.ecr.aws golang:1.24-bookworm — required for Go 1.24 module builds (make build),
# Debian bookworm apt packages (pinned nodejs for calibrate.js), and CGO-free static binaries.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    GOTOOLCHAIN=local \
    GO111MODULE=on \
    CGO_ENABLED=0 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.lock /tmp/requirements.lock

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema=2.2.0-1 \
        ca-certificates=20230311+deb12u1 \
        make=4.3-4.1 \
        nodejs=18.20.4+dfsg-1~deb12u2 \
        python3=3.11.2-1+b1 \
        python3-pip=23.0.1+dfsg-1 \
        tmux=3.3a-3 \
    && pip3 install --break-system-packages --no-cache-dir \
        --require-hashes --no-deps -r /tmp/requirements.lock \
    && groupadd -r taskagent \
    && useradd -r -g taskagent -d /app -s /bin/bash taskagent \
    && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/requirements.lock

WORKDIR /app

COPY --chmod=444 go.mod Makefile /app/
COPY --chmod=444 spec/ /app/spec/
COPY --chmod=444 fixtures/ /app/fixtures/
COPY --chmod=444 assets/ /app/assets/
COPY --chown=taskagent:taskagent bin/ /app/bin/
COPY --chown=taskagent:taskagent engine/ /app/engine/

RUN mkdir -p /app/build /opt/verifier-baseline \
    && cp -a /app/fixtures /app/spec /app/assets /opt/verifier-baseline/ \
    && cp /app/Makefile /app/go.mod /opt/verifier-baseline/ \
    && chown taskagent:taskagent /app/build \
    && chmod u+w /app/build
