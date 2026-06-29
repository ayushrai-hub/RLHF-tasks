FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

LABEL task="java-ffmpeg-hls-evidence" rev="2026-06-20-r1-initial-scaffold"
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        curl \
        ca-certificates \
        openssl \
        tmux \
        asciinema \
        jq \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Pre-download verifier Python wheels then install them into a dedicated
# build-time venv at /opt/test-venv so test.sh never runs `pip install` at
# verifier-runtime (human reviewer round 9). The wheels stay at
# /opt/test-wheels as a fallback evidence trail; the venv is what test.sh
# activates. python3-venv is required because Debian/Ubuntu split it from
# the base python3 package.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/test-wheels \
    && python3 -m pip download --no-cache-dir --dest /opt/test-wheels \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        JPype1==1.5.0 \
        jaydebeapi==1.2.3 \
    && python3 -m venv /opt/test-venv \
    && /opt/test-venv/bin/pip install --no-cache-dir --no-index \
        --find-links /opt/test-wheels \
        pytest==8.4.1 pytest-json-ctrf==0.3.5 \
        JPype1==1.5.0 jaydebeapi==1.2.3

# Pre-stage the H2 JDBC driver at /opt/jars (offline, sha256-verified).
RUN mkdir -p /opt/jars \
    && curl -fsSL -o /opt/jars/h2-2.2.224.jar \
        https://repo1.maven.org/maven2/com/h2database/h2/2.2.224/h2-2.2.224.jar \
    && echo "b9d8f19358ada82a4f6eb5b174c6cfe320a375b5a9cb5a4fe456d623e6e55497  /opt/jars/h2-2.2.224.jar" | sha256sum -c -

# Pre-stage the evidence-vault master key (32 raw bytes hex-encoded) at
# /opt/evidence_keys/master.key.hex. The key is generated at image-build time
# via openssl so it is never present in the submitted source. The agent reads
# this runtime path through KeyStore.java; the verifier reads it directly
# when it needs to derive expected wrapped values.
RUN mkdir -p /opt/evidence_keys \
    && openssl rand -hex 32 | tr -d '\n' > /opt/evidence_keys/master.key.hex \
    && chmod 0444 /opt/evidence_keys/master.key.hex

RUN mkdir -p /app/data /app/src /app/build /app/fixtures /app/reports /app/scripts

# Generate seven valid MPEG-TS plaintext segments via ffmpeg so the M3
# remux step (which uses ffmpeg -f concat -c copy) can actually concat
# them into a playable MP4. The segments are written to a private
# staging dir; FixtureGen reads them and encrypts them in-place.
RUN mkdir -p /opt/plain_segments \
    && for i in 0 1 2 3 4 5 6 ; do \
         ffmpeg -hide_banner -loglevel error -nostdin -y \
           -f lavfi -i "color=c=blue:s=160x120:d=1:r=10" \
           -f lavfi -i "sine=frequency=$((400 + i * 50)):duration=1" \
           -c:v libx264 -preset ultrafast -pix_fmt yuv420p -g 10 \
           -c:a aac -ar 8000 -b:a 32k \
           -muxdelay 0 -muxpreload 0 \
           -f mpegts /opt/plain_segments/$(printf "%04d" $i).ts ; \
       done \
    && ls -la /opt/plain_segments

# Build the fixture generator into a stand-alone jar that the image runs
# once at build time. The agent never sees this source - it is consumed
# inside the Dockerfile and removed.
RUN mkdir -p /opt/fixturegen/src/fixturegen /opt/fixturegen/classes
COPY source/fixturegen/FixtureGen.java /opt/fixturegen/src/fixturegen/FixtureGen.java
RUN javac -d /opt/fixturegen/classes /opt/fixturegen/src/fixturegen/FixtureGen.java \
    && cd /opt/fixturegen/classes \
    && jar cfe /opt/fixturegen/fixturegen.jar fixturegen.FixtureGen fixturegen \
    && rm -rf /opt/fixturegen/src /opt/fixturegen/classes

# Generate the corrupted HLS export + wrapped-key JSON + expected audit
# vectors. Pass the master-key path, the plain-segments staging dir, and
# a fixed seed so fixtures are reproducible.
RUN java -cp /opt/fixturegen/fixturegen.jar fixturegen.FixtureGen \
        /opt/evidence_keys/master.key.hex \
        /app/data \
        /app/fixtures \
        /opt/plain_segments \
        1750000000 \
    && ls -la /app/fixtures \
    && rm -rf /opt/plain_segments

# Pre-bake a read-only pristine copy of the broken recovery_config.json so
# the verifier always restores a known-good baseline, even if the agent has
# already run `recover-config` (which rewrites the mutable copy under
# /app/data). Without this baseline, a test that copies the mutable file as
# its baseline would be poisoned and idempotency / repair tests would fail.
RUN cp /app/data/recovery_config.json /app/fixtures/_pristine_config.json \
    && chmod 0444 /app/fixtures/_pristine_config.json

# Copy spec docs into /app/docs so the agent (and verifier) can read them.
COPY docs/API_SPEC.md        /app/docs/API_SPEC.md
COPY docs/h2-schema.md       /app/docs/h2-schema.md
COPY docs/hls-recovery.md    /app/docs/hls-recovery.md
COPY docs/audit-chain.md     /app/docs/audit-chain.md
COPY docs/validator-rules.md /app/docs/validator-rules.md
COPY docs/error-codes.md     /app/docs/error-codes.md

# Copy the minimal Java skeleton tree (NotImplementedError stubs the agent
# will replace).
RUN mkdir -p /app/src/com/evidence/recovery
COPY source/recovery/RecoveryMain.java     /app/src/com/evidence/recovery/RecoveryMain.java
COPY source/recovery/KeyStore.java         /app/src/com/evidence/recovery/KeyStore.java
COPY source/recovery/EvidenceDb.java       /app/src/com/evidence/recovery/EvidenceDb.java
COPY source/recovery/RecoveryConfig.java   /app/src/com/evidence/recovery/RecoveryConfig.java
COPY source/recovery/SegmentDecryptor.java /app/src/com/evidence/recovery/SegmentDecryptor.java
COPY source/recovery/AuditLog.java         /app/src/com/evidence/recovery/AuditLog.java
COPY source/recovery/FfmpegMux.java        /app/src/com/evidence/recovery/FfmpegMux.java
COPY source/recovery/HlsValidator.java     /app/src/com/evidence/recovery/HlsValidator.java
COPY source/recovery/HexUtil.java          /app/src/com/evidence/recovery/HexUtil.java
COPY source/recovery/JsonOut.java          /app/src/com/evidence/recovery/JsonOut.java
COPY source/recovery/MiniJson.java         /app/src/com/evidence/recovery/MiniJson.java

# Pre-compile the skeleton so the image always ships a runnable (but
# stubbed) build at /app/build.
RUN javac -cp "/opt/jars/*" -d /app/build /app/src/com/evidence/recovery/*.java
