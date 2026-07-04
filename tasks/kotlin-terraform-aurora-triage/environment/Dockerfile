FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        python3-pip \
        python3-venv \
        wget \
        unzip \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

# Install Kotlin compiler CLI (v1.9.22)
RUN wget -q https://github.com/JetBrains/kotlin/releases/download/v1.9.22/kotlin-compiler-1.9.22.zip \
    && echo "88B39213506532C816FF56348C07BBEEFE0C8D18943BFFBAD11063CF97CAC3E6  kotlin-compiler-1.9.22.zip" | sha256sum -c - \
    && unzip kotlin-compiler-1.9.22.zip -d /usr/local \
    && rm kotlin-compiler-1.9.22.zip
ENV PATH="${PATH}:/usr/local/kotlinc/bin"

# Pre-download and cache Gson for offline compilation
RUN mkdir -p /usr/share/java \
    && wget -q -O /usr/share/java/gson.jar https://repo1.maven.org/maven2/com/google/code/gson/gson/2.10.1/gson-2.10.1.jar \
    && echo "4241C14A7727C34FEEA6507EC801318A3D4A90F070E4525681079FB94EE4C593  /usr/share/java/gson.jar" | sha256sum -c -

# Install verifier requirements in isolated venv
COPY verifier-requirements.lock /tmp/verifier-requirements.lock
RUN python3 -m venv --system-site-packages /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --require-hashes --no-deps --no-cache-dir \
        -r /tmp/verifier-requirements.lock

WORKDIR /app

# Copy agent-visible files
COPY terraform/ /app/terraform/
COPY docs/ /app/docs/
COPY dataset/ /app/dataset/
COPY incoming_frames/ /app/incoming_frames/

# Create output and source directories
RUN mkdir -p /app/src /app/output /app/models
