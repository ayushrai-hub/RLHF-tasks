FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  tmux=3.3a-3 \
  asciinema=2.2.0-1 \
  python3=3.11.2-1+b1 \
  python3-venv=3.11.2-1+b1 \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier
RUN /opt/verifier/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5
ENV PATH=/opt/verifier/bin:${PATH}

RUN npm install -g tsx@4.19.2 typescript@5.7.3

COPY . /app/environment
RUN mkdir -p /app/bin /app/output
CMD ["node", "-e", "console.log('Environment ready')"]
