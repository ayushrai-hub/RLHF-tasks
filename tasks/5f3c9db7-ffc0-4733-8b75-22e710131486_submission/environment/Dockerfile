FROM golang:1.22-bookworm@sha256:1f298b0c9fecdf504389a0329236f948cc04a566a2bb32337207cbaaa2f8177c

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates=20230311+deb12u1 patch=2.7.6-7 python3-minimal=3.11.2-1+b1 python3-pip=23.0.1+dfsg-1 python-is-python3=3.11.2-1+deb12u1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python \
    && python -m pip install --break-system-packages --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY README.md /app/environment/README.md
COPY src/. /app/environment/
COPY data/config /app/environment/data/config
COPY data/fixtures /app/fixtures

RUN cd /app/environment \
    && go mod download \
    && go build -o /app/logrecover ./cmd/logrecover \
    && rm -rf /root/.cache/go-build

ENV PATH="/usr/local/go/bin:/app:${PATH}"
