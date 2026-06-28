FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        cmake \
        make \
        python-is-python3 \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY CMakeLists.txt /app/CMakeLists.txt
COPY src/ /app/src/
COPY docs/ /app/docs/
COPY input/ /app/input/
COPY scripts/ /app/scripts/

WORKDIR /app
