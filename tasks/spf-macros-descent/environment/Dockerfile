FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV PATH=/usr/local/go/bin:$PATH
ENV GOTOOLCHAIN=local
ENV GOPROXY=off
ENV CGO_ENABLED=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        python3 \
        python3-pip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt

WORKDIR /app

COPY app/ /app/

RUN bash -lc 'go version' \
    && cd /app/spf \
    && go mod tidy \
    && printf 'package main\nfunc main(){}\n' > /tmp/warm.go \
    && go build -o /tmp/warm /tmp/warm.go \
    && rm -f /tmp/warm /tmp/warm.go
