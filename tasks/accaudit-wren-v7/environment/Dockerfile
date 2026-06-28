FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build wren-cli from source (pinned commit; fixes glibc >= 2.34 build)
RUN git clone https://github.com/wren-lang/wren-cli.git /tmp/wren-cli \
    && cd /tmp/wren-cli \
    && git checkout 18553636618a4d33f10af9b5ab92da6431784a8c \
    && make -C projects/make \
    && install -m 755 bin/wren_cli /usr/local/bin/wren_cli \
    && rm -rf /tmp/wren-cli

# Non-canonical base justification: this task targets Wren, a language not covered
# by the canonical t-bench base-image list. wren_cli has no apt package or official
# binary release and must be compiled from source (builder stage above), so we use
# the canonical digest-pinned Ubuntu 24.04 image for both stages. tmux + asciinema
# (required for terminal-session recording) are installed explicitly below so the
# agent harness never has to install them at runtime.
FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932

LABEL revision="v7-spec-clarify-decimal-missingfield"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    tmux \
    asciinema \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/wren_cli /usr/local/bin/wren_cli

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --require-hashes --no-deps --break-system-packages -r /tmp/requirements.txt

WORKDIR /app
COPY app/ /app/
