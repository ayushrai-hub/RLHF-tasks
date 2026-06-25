FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -o Acquire::Retries=3 update && \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        make=4.3-4.1 \
        ca-certificates=20230311+deb12u1 \
        python3=3.11.2-1+b1 \
        python3-pip=23.0.1+dfsg-1 \
        python3-venv=3.11.2-1+b1 \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages --retries 3 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

COPY app/ /app/

RUN mkdir -p /app/output /tmp/go-cache /tmp/go-path

ENV GOFLAGS=-mod=mod
ENV GOCACHE=/tmp/go-cache
ENV GOPATH=/tmp/go-path
ENV GOPROXY=off
ENV GOSUMDB=off
ENV GOTOOLCHAIN=local
ENV CGO_ENABLED=0
ENV XDG_CACHE_HOME=/tmp
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV HOME=/root
ENV PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go && \
    ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt

RUN printf '%s\n' \
    'export PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
    'export GOCACHE=/tmp/go-cache' \
    'export GOPATH=/tmp/go-path' \
    'export GOFLAGS=-mod=mod' \
    'export GOPROXY=off' \
    'export GOSUMDB=off' \
    'export GOTOOLCHAIN=local' \
    'export CGO_ENABLED=0' \
    'export XDG_CACHE_HOME=/tmp' \
    'export HOME=${HOME:-/root}' \
    > /etc/profile.d/go.sh && chmod 0644 /etc/profile.d/go.sh

RUN printf '\n%s\n' \
    '# go toolchain bootstrap (twamp audit)' \
    'export PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
    'export GOCACHE=/tmp/go-cache' \
    'export GOPATH=/tmp/go-path' \
    'export GOFLAGS=-mod=mod' \
    'export GOPROXY=off' \
    'export GOSUMDB=off' \
    'export GOTOOLCHAIN=local' \
    'export CGO_ENABLED=0' \
    'export XDG_CACHE_HOME=/tmp' \
    'export HOME=${HOME:-/root}' \
    >> /etc/bash.bashrc

RUN printf '%s\n' \
    'PATH="/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' \
    'GOCACHE="/tmp/go-cache"' \
    'GOPATH="/tmp/go-path"' \
    'GOFLAGS="-mod=mod"' \
    'GOPROXY="off"' \
    'GOSUMDB="off"' \
    'GOTOOLCHAIN="local"' \
    'CGO_ENABLED="0"' \
    'XDG_CACHE_HOME="/tmp"' \
    'HOME="/root"' \
    > /etc/environment

RUN bash -lc 'which go && go version' && \
    bash  -c 'which go && go version' && \
    env -i bash -lc 'which go && go version' && \
    env -i bash  -c 'which go && go version' && \
    cd /app && go build std

RUN cd /app && \
    (go build -trimpath -o /tmp/twamp-prewarm ./cmd/auditor || true) && \
    rm -f /tmp/twamp-prewarm

CMD ["/bin/bash"]
