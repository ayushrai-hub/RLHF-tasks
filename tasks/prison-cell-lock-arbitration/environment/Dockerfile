FROM docker.io/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TMUX_TMPDIR=/var/tmp/tmux

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv cargo rustc \
    asciinema \
    build-essential \
    ca-certificates \
    gcc \
    make \
    ncurses-term \
    pkg-config \
    tmux \
    && mkdir -p /var/tmp/tmux \
    && chmod 1777 /var/tmp/tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY runtime/tmux.conf /etc/tmux.conf
COPY Cargo.toml /app/environment/Cargo.toml
COPY Cargo.lock /app/environment/Cargo.lock
COPY fac_b2 /app/environment/fac_b2
COPY q3_v9 /app/environment/q3_v9
COPY qtr_w4 /app/environment/qtr_w4
COPY hash_n6 /app/environment/hash_n6
COPY wav_h8 /app/environment/wav_h8
COPY fixtures /app/environment/fixtures
COPY scripts /app/environment/scripts
COPY docs /app/environment/docs

RUN chmod +x /app/environment/scripts/run_sim_driver.sh \
    && cd /app/environment \
    && for attempt in 1 2 3; do \
         cargo build --locked --release --bin facility_sim && break; \
         if [ "$attempt" -eq 3 ]; then exit 1; fi; \
         sleep 15; \
       done
