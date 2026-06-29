FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    GOTOOLCHAIN=local \
    GOPROXY=off \
    GOSUMDB=off \
    PATH="/usr/local/go/bin:${PATH}"

COPY debs/ /tmp/debs/
RUN test -n "$(find /tmp/debs -maxdepth 1 -name '*.deb' -print -quit)" \
    && dpkg -i /tmp/debs/*.deb \
    && apt-get clean \
    && rm -rf /tmp/debs /var/lib/apt/lists/* \
    && command -v escript >/dev/null \
    && tmux -V \
    && asciinema --version \
    && go version \
    && python3 --version

WORKDIR /root
COPY task_file/ /

RUN chmod +x /opt/beamjournal/bin/image-setup.sh /usr/local/sbin/beamjournal-supervise /usr/local/lib/beamjournal/seed.escript \
    && bash /opt/beamjournal/bin/image-setup.sh

CMD ["/bin/bash"]

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive \
    GOTOOLCHAIN=local \
    GOPROXY=off \
    GOSUMDB=off \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/go/bin:${PATH}"

COPY --from=builder /usr/local/go /usr/local/go
COPY requirements.lock /tmp/requirements.lock
RUN apt-get update && apt-get install -y --no-install-recommends --no-upgrade bash ca-certificates procps python3 && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock \
    && mkdir -p /logs/agent /logs/artifacts /logs/verifier \
    && go version \
    && python --version \
    && python -m pytest --version

COPY debs/ /tmp/debs/
RUN test -n "$(find /tmp/debs -maxdepth 1 -name '*.deb' -print -quit)" \
    && dpkg -i /tmp/debs/*.deb \
    && apt-get clean \
    && rm -rf /tmp/debs /var/lib/apt/lists/* \
    && command -v escript >/dev/null \
    && tmux -V \
    && asciinema --version \
    && python3 --version

WORKDIR /root
COPY task_file/ /

RUN chmod +x /opt/beamjournal/bin/image-setup.sh /usr/local/sbin/beamjournal-supervise /usr/local/lib/beamjournal/seed.escript \
    && bash /opt/beamjournal/bin/image-setup.sh

CMD ["/bin/bash"]
