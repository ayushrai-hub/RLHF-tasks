FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip tmux asciinema \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY task_file/ /app/task_file/
RUN rm -rf /app/task_file/output_data \
    && mkdir -p /app/task_file/output_data /app/task_file/src

WORKDIR /app
