FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14 AS jdkbase

FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3 \
    tmux \
    asciinema \
 && rm -rf /var/lib/apt/lists/*

ENV SCALA_VERSION=3.3.4
RUN curl -fsSL "https://github.com/scala/scala3/releases/download/${SCALA_VERSION}/scala3-${SCALA_VERSION}.tar.gz" -o /tmp/scala3.tgz \
 && mkdir -p /opt/scala3 \
 && tar -xzf /tmp/scala3.tgz -C /opt/scala3 --strip-components=1 \
 && rm /tmp/scala3.tgz

RUN mkdir -p /opt/abac-libs \
 && curl -fsSL "https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.45.3.0/sqlite-jdbc-3.45.3.0.jar" -o /opt/abac-libs/sqlite-jdbc.jar \
 && curl -fsSL "https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.13/slf4j-api-2.0.13.jar" -o /opt/abac-libs/slf4j-api.jar \
 && curl -fsSL "https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/2.0.13/slf4j-simple-2.0.13.jar" -o /opt/abac-libs/slf4j-simple.jar

COPY --from=jdkbase /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"

COPY requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/verifier-venv \
 && /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
 && rm /tmp/requirements.lock

WORKDIR /app
COPY app/ /app/
RUN sed -i 's/\r$//' /app/scripts/build.sh /app/bin/abac-ingest /app/bin/abac-export /app/bin/abac-serve \
 && chmod +x /app/scripts/build.sh /app/bin/abac-ingest /app/bin/abac-export /app/bin/abac-serve \
 && python3 /app/data/make_sample_abwf.py \
 && ABAC_BUILD_CHECK=0 bash /app/scripts/build.sh \
 && ln -snf /app /app/environment

CMD ["bash"]
