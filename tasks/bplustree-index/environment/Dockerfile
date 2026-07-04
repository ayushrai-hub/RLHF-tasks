FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux \
    asciinema \
    ca-certificates \
    curl \
    make \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/0.5.11/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
RUN uv venv /opt/verifier --python 3.13 \
    && uv pip install --python /opt/verifier/bin/python pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY Makefile /app/Makefile
COPY include /app/include
COPY src /app/src
COPY docs /app/docs
COPY data /app/data

RUN make
