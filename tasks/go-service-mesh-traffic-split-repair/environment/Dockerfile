FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/go/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3=3.11.2-1+b1 \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    curl=7.88.1-10+deb12u14 \
    patch=2.7.6-7 \
    python3-pip=23.0.1+dfsg-1 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY splitter/ /app/environment/splitter/
COPY config/ /app/environment/config/
COPY data/ /app/environment/data/
COPY common/ /app/environment/common/
COPY docs/ /app/environment/docs/

RUN mkdir -p /app/bin /app/output \
    && cd /app/environment/splitter && go build -o /app/bin/splitter .

CMD ["/bin/bash"]
