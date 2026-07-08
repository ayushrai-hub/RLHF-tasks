# Debian final runtime is used because this task combines Rust, C, Lua, Bash, and Python verifier tools in one container.
FROM debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

WORKDIR /app

RUN apt-get update     && apt-get install -y --no-install-recommends         tmux         asciinema         ca-certificates         python3         python3-pip         rustc         cargo         gcc         make         lua5.4         libc6-dev     && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir     pytest==8.4.1     pytest-json-ctrf==0.3.5

COPY app/ /app/
