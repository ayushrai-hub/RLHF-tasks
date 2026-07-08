FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

RUN apt-get update \
    && apt-get install -y --no-install-recommends asciinema bash git patch python3 python3-venv ripgrep tmux util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/verifier

COPY requirements.lock /tmp/requirements.lock
RUN /opt/verifier/bin/pip install --no-cache-dir -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

ENV PATH="/opt/verifier/bin:${PATH}"
WORKDIR /app
COPY repo/ /app/
RUN chmod +x /app/bin/transfer-pruner.js \
    && npm run check \
    && git init -q \
    && git config user.email task@example.com \
    && git config user.name task \
    && git add -A \
    && git commit -q -m "initial task state"
