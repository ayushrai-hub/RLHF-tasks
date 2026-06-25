# syntax=docker/dockerfile:1
# python:3.13-slim-bookworm: sanctioned offline pytest verifier base; OpenJDK 17 and Gradle added for the Kotlin CLI build.
FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless=17.0.19+10-1~deb12u2 \
        curl=7.88.1-10+deb12u14 \
        ca-certificates=20230311+deb12u1 \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
        unzip=6.0-28 \
    && rm -rf /var/lib/apt/lists/*

ARG GRADLE_VERSION=8.7
ARG GRADLE_SHA256=544c35d6bd849ae8a5ed0bcea39ba677dc40f49df7d1835561582da2009b961d
RUN curl --proto '=https' --tlsv1.2 -fsSL \
      "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" \
      -o /tmp/gradle.zip \
    && echo "${GRADLE_SHA256}  /tmp/gradle.zip" | sha256sum -c - \
    && unzip -q /tmp/gradle.zip -d /opt \
    && rm -f /tmp/gradle.zip \
    && ln -sf "/opt/gradle-${GRADLE_VERSION}/bin/gradle" /usr/local/bin/gradle

RUN python3 -m venv /opt/verifier \
    && /opt/verifier/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

ENV PATH=/opt/verifier/bin:/usr/local/bin:${PATH}
ENV GRADLE_USER_HOME=/app/.gradle

WORKDIR /app

COPY settings.gradle.kts build.gradle.kts gradle.properties ./
COPY q7cli/ ./q7cli/
COPY q7harvest/ ./q7harvest/
COPY q8strace/ ./q8strace/
COPY q9lsof/ ./q9lsof/
COPY r4policy/ ./r4policy/
COPY r5decoy/ ./r5decoy/
COPY docs/ ./docs/
COPY policy/ ./policy/
COPY data/ ./data/
COPY harness/ ./harness/
COPY config/ ./config/
COPY --chmod=0755 scripts/ ./scripts/

RUN gradle :q7cli:jar --quiet \
    && mkdir -p /app/build/libs \
    && cp /app/q7cli/build/libs/trace-audit-cli-0.1.0.jar /app/build/libs/trace-audit-cli.jar
