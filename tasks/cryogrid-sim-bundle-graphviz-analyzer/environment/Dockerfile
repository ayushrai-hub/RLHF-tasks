FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

LABEL org.opencontainers.image.base.name="public.ecr.aws/docker/library/gcc:13-bookworm"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    cmake \
    graphviz \
    libgraphviz-dev \
    nlohmann-json3-dev \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

ENV PATH="/opt/verifier-venv/bin:${PATH}"

WORKDIR /app

COPY CMakeLists.txt /app/CMakeLists.txt
COPY include/ /app/include/
COPY src/ /app/src/
COPY docs/ /app/docs/
COPY fixtures/ /app/fixtures/
COPY scripts/ /app/scripts/
COPY README.md /app/README.md
COPY verifier-fixtures/bundles/ /opt/verifier-fixtures/bundles/

RUN mkdir -p /app/docs/validation-memo /app/output /app/state \
 && python3 /app/scripts/generate_validation_memo.py \
    > /app/docs/validation-memo/cryogrid-thermal-review.md \
 && cmake -B /app/build -S /app \
 && cmake --build /app/build -j"$(nproc)"
