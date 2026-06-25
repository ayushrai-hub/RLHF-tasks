FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# JDK 21 comes from the base image. python and pip are layered in for the
# verifier's pytest, which is installed from pip below.
RUN apt-get update && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Verifier dependencies, pinned. This base manages its python with the
# system package manager, but pip on this base is not externally managed.
RUN pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY app/ /app/

# Build the jar at image-build time so the container starts from a
# runnable state. The bundled source still has the defects in it, so
# the cases come out wrong until the fixes land, but it runs.
RUN cd /app && ./build.sh

CMD ["/app/entrypoint.sh"]
