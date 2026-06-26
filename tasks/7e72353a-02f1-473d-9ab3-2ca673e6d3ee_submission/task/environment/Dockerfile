FROM golang:1.22-bookworm

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        ca-certificates \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

COPY task_file/opt/ /opt/
COPY task_file/etc/ /etc/
COPY task_file/var/spool/ /var/spool/
COPY task_file/var/lib/ /var/lib/

RUN chmod +x \
    /opt/change-freeze/bin/change-freeze \
    /opt/change-freeze/bin/build.sh \
    /opt/change-freeze/bin/config_guard \
    /opt/change-freeze/bin/smoke-check \
    /opt/change-freeze/bin/sync_vendor.sh \
    && mkdir -p /var/lib/change-freeze/out

WORKDIR /opt/change-freeze
