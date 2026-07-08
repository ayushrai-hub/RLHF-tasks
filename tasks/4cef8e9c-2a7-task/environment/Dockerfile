FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

LABEL org.opencontainers.image.source="marrow-huffman-container" \
      org.opencontainers.image.revision="marrow-huffman-container-v1" \
      org.opencontainers.image.created="2026-06-24T00:00:00Z" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="UNLICENSED"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    MARROW_APP=/app/marrow \
    MARROW_SPEC=/app/marrow/docs/spec.md

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        python3 \
        python3-pip \
        python3-venv \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-verifier.txt /tmp/requirements-verifier.txt
RUN python3 -m venv "$VIRTUAL_ENV" \
    && python -m pip install --no-cache-dir -r /tmp/requirements-verifier.txt \
    && rm /tmp/requirements-verifier.txt

COPY marrow/README.md /app/marrow/README.md
COPY marrow/docs/ /app/marrow/docs/
COPY marrow/programs/ /app/marrow/programs/
COPY marrow/src/ /app/marrow/src/

WORKDIR /app/marrow

RUN javac -d out src/marrow/*.java
