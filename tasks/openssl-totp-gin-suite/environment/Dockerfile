FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends make=4.3-4.1 build-essential=12.9 python3=3.11.2-1+b1 \
  libssl-dev=3.0.20-1~deb12u1 \
  libssl3=3.0.20-1~deb12u1 \
  libcurl4-openssl-dev=7.88.1-10+deb12u14 \
  curl=7.88.1-10+deb12u14 \
  ca-certificates=20230311+deb12u1 \
  python3-venv=3.11.2-1+b1 \
  tmux=3.3a-3 \
  asciinema=2.2.0-1 \
  && rm -rf /var/lib/apt/lists/*

# Verifier tooling is baked at image build; runtime has allow_internet=false.
RUN curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN uv python install 3.13.9 \
  && uv venv /opt/verifier-venv --python 3.13.9 \
  && uv pip install --python /opt/verifier-venv/bin/python \
      pytest==8.4.1 pytest-json-ctrf==0.3.5 \
  && /opt/verifier-venv/bin/pytest --version

ENV PATH="/opt/verifier-venv/bin:/usr/local/go/bin:${PATH}"

RUN curl -fsSL https://go.dev/dl/go1.22.5.linux-amd64.tar.gz -o /tmp/go.tgz \
  && tar -C /usr/local -xzf /tmp/go.tgz \
  && rm /tmp/go.tgz

COPY m3_host /tmp/m3_host
RUN cd /tmp/m3_host && go mod download && CGO_ENABLED=0 go build -o /app/bin/m3_host . \
  && rm -rf /tmp/m3_host /root/go/pkg/mod /root/.cache/go-build

COPY m3_host/config /app/environment/m3_host/config
COPY c9_drv /app/environment/c9_drv
COPY c7_rack /app/environment/c7_rack
COPY pkt_vend /app/environment/pkt_vend
COPY c8_wrap /app/environment/c8_wrap
COPY pkt_tools /app/environment/pkt_tools
COPY docs /app/environment/docs
COPY data /app/environment/data
COPY scripts /app/environment/scripts

RUN chmod +x /app/environment/scripts/*.sh /app/environment/scripts/step_driver.py
RUN make -C /app/environment/c9_drv all

RUN mkdir -p /app/output /app/bin
