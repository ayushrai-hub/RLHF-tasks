FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema ca-certificates git procps python3 python3-pip tmux \
    && rm -rf /var/lib/apt/lists/*
RUN PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install --no-cache-dir \
        pytest==8.4.1 pytest-json-ctrf==0.3.5
WORKDIR /app
CMD ["sleep", "infinity"]
