FROM --platform=linux/amd64 public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    curl \
    httpie \
    maven \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
COPY docker/install_probe_fixtures.sh /tmp/install_probe_fixtures.sh
COPY docker/rebuild-buoy-spectra.sh /opt/verifier-scripts/rebuild-buoy-spectra
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir -r /tmp/requirements.lock \
 && chmod +x /opt/verifier-scripts/rebuild-buoy-spectra

ENV PATH="/opt/verifier-scripts:/opt/verifier-venv/bin:${PATH}"

WORKDIR /app

COPY pom.xml ./
RUN mvn -q -B -f /app/pom.xml -DskipTests dependency:go-offline
COPY src/ ./src/
COPY profiles/ ./profiles/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY build/ ./build/
COPY README.md ./

RUN /opt/verifier-venv/bin/python3 build/gen_dossier.py \
 && /opt/verifier-venv/bin/python3 build/gen_fixtures.py \
 && bash /tmp/install_probe_fixtures.sh \
 && chmod +x /app/scripts/*.sh \
 && mvn -q -B -f /app/pom.xml -DskipTests package \
 && mkdir -p /app/output \
 && rm -f /tmp/install_probe_fixtures.sh /tmp/requirements.lock
