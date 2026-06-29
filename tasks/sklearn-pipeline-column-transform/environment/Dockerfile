
FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless=17.0.19+10-1~deb12u2 \
        g++=4:12.2.0-3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY app/ /build/
RUN chmod +x docker-entrypoint.sh scripts/run_integration_tests.sh java/compile.sh native/build_native.sh \
    && echo "57928d6e5a6edeb2abd3770a8f95ba44dce45f3b23b7a9dc2b309c581552a78b  /build/java/lib/gson-2.11.0.jar" | sha256sum -c - \
    && bash /build/native/build_native.sh \
    && bash /build/java/compile.sh

FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
COPY requirements.lock /tmp/requirements.lock
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless=17.0.19+10-1~deb12u2 \
        g++=4:12.2.0-3 \
        python3 python3-pip ca-certificates procps tmux asciinema bash \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --break-system-packages \
        --require-hashes -r /tmp/requirements.lock

WORKDIR /app
COPY app/ /app/
COPY --from=builder /build/native/ /app/native/
COPY --from=builder /build/java/build/ /app/java/build/
RUN echo "57928d6e5a6edeb2abd3770a8f95ba44dce45f3b23b7a9dc2b309c581552a78b  /app/java/lib/gson-2.11.0.jar" | sha256sum -c - \
    && chmod +x docker-entrypoint.sh scripts/run_integration_tests.sh java/compile.sh native/build_native.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["idle"]
