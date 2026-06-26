FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    python3-venv=3.11.2-1+b1 \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

ENV PATH="/opt/verifier-venv/bin:${PATH}"

COPY package.json package-lock.json /app/environment/
COPY starfield-switchboard /app/environment/starfield-switchboard
COPY scorecard-cases /app/environment/scorecard-cases
COPY docs /app/environment/docs
COPY ops /app/ops
COPY sfdata /app/sfdata

WORKDIR /app/environment
RUN npm ci --no-audit --no-fund \
    && npm run build \
    && chmod +x /app/ops/sfdesk \
    && mkdir -p /app/output

WORKDIR /app
CMD ["bash"]
