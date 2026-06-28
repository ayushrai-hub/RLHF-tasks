FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS probe
WORKDIR /b
COPY probesrc/main.go .
RUN printf 'module m\ngo 1.24\n' > go.mod \
    && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/catalog-probe main.go

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb AS fixtures
WORKDIR /b
COPY gensrc/codec.py gensrc/feedgen.py ./
RUN mkdir -p /out && python feedgen.py /out

FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16 postgresql-client-16 \
        ca-certificates curl gnupg sudo procps \
        tmux asciinema \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /tmp/nodesource.sigfile \
    && echo "b42e0321dabdc24e892115da705cf061167eac12a317f23d329862d0aa0a271d  /tmp/nodesource.sigfile" | sha256sum -c - \
    && gpg --dearmor < /tmp/nodesource.sigfile > /usr/share/keyrings/nodesource.gpg \
    && rm /tmp/nodesource.sigfile \
    && echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.9.5
ARG UV_SHA256_X86_64=2cf10babba653310606f8b49876cfb679928669e7ddaa1fb41fb00ce73e64f66
ARG UV_SHA256_AARCH64=9db0c2f6683099f86bfeea47f4134e915f382512278de95b2a0e625957594ff3
RUN ARCH=$(uname -m) \
 && case "$ARCH" in \
      x86_64)  UV_TAR=uv-x86_64-unknown-linux-gnu.tar.gz;  UV_SHA="${UV_SHA256_X86_64}"  ;; \
      aarch64) UV_TAR=uv-aarch64-unknown-linux-gnu.tar.gz; UV_SHA="${UV_SHA256_AARCH64}" ;; \
      *) echo "unsupported arch: ${ARCH}" >&2; exit 1 ;; \
    esac \
 && curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${UV_TAR}" -o /tmp/uv.tar.gz \
 && echo "${UV_SHA}  /tmp/uv.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/uv.tar.gz -C /usr/local/bin --strip-components=1 \
 && rm /tmp/uv.tar.gz \
 && /usr/local/bin/uv venv /opt/verifier-venv -p 3.13 \
 && /usr/local/bin/uv pip install --python /opt/verifier-venv/bin/python \
        pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN mkdir -p /app/data /app/ref /app/docs /var/lib/csv-importer /var/log/svc \
             /var/run/postgresql /var/log/postgresql /logs/verifier /logs/agent

COPY entrypoint.sh                       /entrypoint.sh
COPY bin/options-pinner                  /usr/local/bin/options-pinner
COPY bin/options-pinner-watchdog         /usr/local/bin/options-pinner-watchdog
COPY app/package.json                    /app/package.json
COPY app/package-lock.json               /app/package-lock.json
COPY app/import.js                       /app/import.js
COPY app/lib/                            /app/lib/
COPY app/bin/                            /app/bin/
COPY docs/catalog-feed-spec.md           /app/docs/catalog-feed-spec.md
COPY pg-config/pg_hba.fragment           /etc/postgresql.pg_hba.fragment
COPY sql/schema.sql                      /app/sql/schema.sql
COPY --from=probe    /out/catalog-probe  /app/ref/catalog-probe
COPY --from=fixtures /out/               /app/data/

RUN cd /app && npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

RUN chown postgres:postgres /var/run/postgresql /var/log/postgresql \
    && chmod +x /entrypoint.sh /app/bin/run-importer /app/ref/catalog-probe \
                /usr/local/bin/options-pinner /usr/local/bin/options-pinner-watchdog

HEALTHCHECK --interval=3s --timeout=5s --start-period=15s --retries=80 \
    CMD test -f /tmp/services-ready || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["sleep", "infinity"]
