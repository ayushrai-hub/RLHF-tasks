# syntax=docker/dockerfile:1.7

# ---- Build stage: warm the Maven cache and produce a startable jar. ----
FROM maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e AS build

WORKDIR /build

COPY app/pom.xml /build/pom.xml
RUN mvn -B -q -DskipTests dependency:go-offline || true

COPY app/src /build/src
RUN mvn -B -q -DskipTests package

# ---- Runtime stage: JDK 21 + agent tooling + offline test venv. ----
FROM eclipse-temurin:21.0.4_7-jdk-jammy@sha256:0472478e22da0f66043fa6acd8cd30126592349f47937adafc2340794e5bf06a AS runtime

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        procps \
        tmux \
        asciinema \
        python3 \
        python3-venv \
        python3-pip \
        maven \
        jq \
    && rm -rf /var/lib/apt/lists/*

# Offline test virtualenv — pinned and fully baked. tests/test.sh must not
# install anything at runtime; allow_internet=false.
RUN python3 -m venv /opt/test-env \
    && /opt/test-env/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        requests==2.32.3

WORKDIR /app

# Source tree the agent edits in place.
COPY app/pom.xml /app/pom.xml
COPY app/src /app/src
COPY app/data /app/data

# DB schema is loaded from a real file path, not classpath: — Spring Boot's
# jar:nested: fat-jar URL scheme resolves classpath: resources unreliably, so
# spring.sql.init.schema-locations points at file:/app/schema.sql instead.
COPY app/src/main/resources/schema.sql /app/schema.sql

# Pre-built jar from build stage so the verifier never pays cold-compile cost.
COPY --from=build /build/target/chronos.jar /app/chronos.jar

# Warm Maven local repo for offline incremental rebuilds.
COPY --from=build /root/.m2 /root/.m2

# H2 DB lives here; create the dir up front.
RUN mkdir -p /app/data

ENV JAVA_OPTS="-XX:+UseG1GC -Xms256m -Xmx1024m"

LABEL org.opencontainers.image.title="chronos-scheduler" \
      org.opencontainers.image.description="Spring Boot Quartz-dialect cron scheduler task environment" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="1.0.1"

CMD ["sleep", "infinity"]
