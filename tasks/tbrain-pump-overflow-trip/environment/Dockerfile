FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

COPY wheels/ /opt/python-wheels/
COPY requirements.lock /opt/python-wheels/requirements.lock
RUN apt-get update && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        coreutils \
        git \
        patch \
        python3 \
        python-is-python3 \
        python3-pip \
        ripgrep \
        sed \
        tmux \
        util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-index \
        --find-links /opt/python-wheels \
        --require-hashes \
        --no-deps \
        -r /opt/python-wheels/requirements.lock

RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go \
    && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt

WORKDIR /app
COPY repo/ /app/

# Warm build: compile the unmodified skeleton during the image build so the
# agent's later rebuild is incremental and the offline runtime never needs the
# network. Then make /app a git repo so the agent's edit tooling works.
RUN go build -o overflow ./cmd/overflow \
    && go vet ./... \
    && git init -q \
    && git config user.email task@example.com \
    && git config user.name task \
    && git add -A \
    && git commit -q -m "initial task state"
