FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac
# infra-retry-v22

RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    python3-pip \
    tmux \
    asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.4.1 pytest-json-report==1.5.0 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY source/ /app/

RUN GOPROXY=https://proxy.golang.org,direct go mod download && go mod tidy

ENV GOPROXY=off

COPY docs/ /docs/
