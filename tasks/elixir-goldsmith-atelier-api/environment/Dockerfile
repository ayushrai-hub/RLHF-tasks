FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
ENV MIX_ENV=prod
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    elixir=1.14.0.dfsg-2 \
    libsqlite3-dev=3.40.1-2+deb12u2 \
    sqlite3=3.40.1-2+deb12u2 \
    build-essential=12.9 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    ca-certificates=20230311+deb12u1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    procps=2:4.0.2-3 \
    && rm -rf /var/lib/apt/lists/*

# Python tools used by the local test runner, installed at build time.
RUN python3 -m venv /opt/test-venv \
 && /opt/test-venv/bin/pip install --no-cache-dir \
        pytest==8.2.0 \
        pytest-json-report==1.5.0 \
        requests==2.32.3 \
        httpx==0.27.2

WORKDIR /app

# Bootstrap Hex / rebar3 with internet that's available only at build time.
RUN mix local.hex --force && mix local.rebar --force

# Stage mix manifest first so cached Elixir deps survive source edits.
COPY task_file/mix.exs /app/mix.exs
COPY task_file/mix.lock /app/mix.lock
COPY task_file/config/config.exs /app/config/config.exs

# Internet is available at build time, so fetch and compile deps now so the
# runtime phase needs no network access at all. HEX_HTTP_CONCURRENCY=1 and a
# longer HEX_HTTP_TIMEOUT make the fetch tolerant of flaky mirrors.
RUN HEX_HTTP_CONCURRENCY=1 HEX_HTTP_TIMEOUT=120 mix deps.get && mix deps.compile

COPY task_file/ /app/

# Compile the application code as well so first request is fast.
RUN mix compile

RUN chmod +x /app/start.sh /app/scripts/*.sh 2>/dev/null || true

ENV DB_PATH=/app/data/atelier.db
ENV PORT=8080

EXPOSE 8080

CMD ["sleep", "infinity"]
