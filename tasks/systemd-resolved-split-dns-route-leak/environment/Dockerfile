FROM ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    bash=5.2.15-2+b9 \
    patch=2.7.6-7 \
    ca-certificates=20230311+deb12u1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY . /app/environment

RUN chmod +x /app/environment/scripts/*.sh /app/environment/migrations/*.sh \
    && /app/environment/scripts/build_all.sh

RUN mkdir -p /app/output

ENV PATH="/app/environment/bin:${PATH}"
ENV RUBYLIB="/app/environment/cmd:/app/environment/r7_lane:/app/environment/n4_cache:/app/environment/v8_scope:/app/environment/q3_trace"
