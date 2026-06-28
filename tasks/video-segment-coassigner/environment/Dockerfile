FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip ca-certificates \
        tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY task_file/ /app/task_file/
RUN mkdir -p /app/task_file/output_data

# Install the TypeScript toolchain at build time so tsc runs offline at solve time.
RUN cd /app/task_file/src && npm ci

WORKDIR /app
