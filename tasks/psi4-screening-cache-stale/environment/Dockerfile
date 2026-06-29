FROM gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    ca-certificates=20230311+deb12u1 \
    cmake=3.25.1-1 \
    curl=7.88.1-10+deb12u14 \
    ncurses-term=6.4-4 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
    zlib1g-dev=1:1.2.13.dfsg-1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

ENV PATH="/opt/verifier-venv/bin:${PATH}"

COPY . /app/environment/

RUN mkdir -p /app/environment/include/nlohmann /app/cases /app/output /app/runtime \
    && curl -fsSL https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp \
       -o /app/environment/include/nlohmann/json.hpp \
    && cp -a /app/environment/cases/. /app/cases/

WORKDIR /app/environment
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --parallel \
    && mkdir -p /app/environment/tools \
    && ln -sf /app/environment/build/p7_run /app/environment/tools/p7_run \
    && ln -sf /app/environment/build/p7_emit /app/environment/tools/p7_emit \
    && ln -sf /app/environment/build/p7_recover /app/environment/tools/p7_recover \
    && ln -sf /app/environment/build/p7_inspect /app/environment/tools/p7_inspect

WORKDIR /app
