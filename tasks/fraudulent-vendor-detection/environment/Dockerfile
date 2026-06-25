FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app

# terminus-2 agent setup runs `tmux -V` and `asciinema --version`. Preinstall both on
# custom bases so runtime apt is skipped (hangs/timeouts when allow_internet=false).
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash=5.2.15-2+b13 \
    ca-certificates=20230311+deb12u1 \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
  && rm -rf /var/lib/apt/lists/* \
  && command -v tmux >/dev/null \
  && command -v asciinema >/dev/null \
  && tmux -V \
  && asciinema --version

COPY . /app/environment

# Verifier-only Python deps (pinned). Installed at build time because allow_internet=false;
# tests/test.sh must not download packages. Pins live in environment/verifier-requirements.txt.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    -r /app/environment/verifier-requirements.txt

RUN mkdir -p /app/bin /app/output \
  && chmod +x /app/environment/tools/runner.sh \
  && cd /app/environment && go mod download \
  && go build -trimpath -ldflags="-s -w" -o /app/bin/vendorlab ./cmd/vendorlab \
  && tmux -V \
  && asciinema --version

# Re-verify session tools and offline verifier stack in the final image layer.
RUN tmux -V \
  && asciinema --version \
  && python3 -m pytest --version
