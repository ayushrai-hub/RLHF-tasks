FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        cmake \
        ninja-build \
        python3 \
        python3-pip \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

WORKDIR /app

ENV CMAKE_BUILD_PARALLEL_LEVEL=2

COPY CMakeLists.txt ./
COPY README.md ./
COPY build_support ./build_support/
COPY include ./include/
COPY src ./src/
COPY docs ./docs/
COPY fixtures ./fixtures/
COPY scripts ./scripts/

RUN chmod +x /app/scripts/build_audit.py \
    && cmake -G Ninja -S /app -B /app/build \
    && cmake --build /app/build -j2

CMD ["/bin/bash"]
