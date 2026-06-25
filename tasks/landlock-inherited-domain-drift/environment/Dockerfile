FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux
ENV PATH="/usr/local/go/bin:${PATH}"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema=2.2.0-1 \
    build-essential=12.9 \
    ca-certificates=20230311+deb12u1 \
    coreutils=9.1-1 \
    gcc=4:12.2.0-3 \
    make=4.3-4.1 \
    ncurses-term=6.4-4 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/tmp/tmux /app/bin /app/output /app/work \
    && chmod 1777 /var/tmp/tmux

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY runtime/tmux.conf /etc/tmux.conf
COPY go.mod /app/environment/go.mod
COPY cmd/ /app/environment/cmd/
COPY Makefile /app/environment/Makefile
COPY d0 /app/environment/d0
COPY lib /app/environment/lib
COPY r1_apply /app/environment/r1_apply
COPY r3_exec /app/environment/r3_exec
COPY r5_audit /app/environment/r5_audit
COPY trace /app/environment/trace
COPY tools /app/environment/tools
COPY tooling /app/environment/tooling
COPY docs /app/environment/docs
COPY fixtures /app/environment/fixtures
COPY cfg /app/environment/cfg
COPY misc /app/environment/misc
COPY q8_actor /app/environment/q8_actor

RUN chmod +x /app/environment/tools/k7_round /app/environment/tools/m4_emit \
    /app/environment/tooling/seal_trace.sh \
    /app/environment/q8_actor/wrap_run.sh /app/environment/q8_actor/direct_run.sh \
    /app/environment/q8_actor/probe_side.sh \
    && cd /app/environment && go mod tidy \
    && go build -o /app/bin/h7stamp ./cmd/h7stamp \
    && make -C /app/environment all

ENV PATH="/app/environment/d0:/app/environment/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
