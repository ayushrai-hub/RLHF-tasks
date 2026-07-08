# Canonical Python base used because the test suite requires pytest +
# requests (Python venv); Tcl runtime is installed via apt below.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        tcl8.6 tcllib \
        libsqlite3-tcl \
        busybox \
        sqlite3 \
        tmux asciinema curl ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock

COPY app/ /app/

RUN mkdir -p /app/data /app/logs /app/run /app/output \
    && chmod +x /app/scripts/build.sh \
               /app/scripts/start_service.sh \
               /app/scripts/stop_service.sh \
               /app/scripts/wait_ready.sh \
               /app/scripts/run_driver.sh \
               /app/db/init_db.sh \
    && chmod +x /app/www/calendar.tcl

CMD ["bash"]
