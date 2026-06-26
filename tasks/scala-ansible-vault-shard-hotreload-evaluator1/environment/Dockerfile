FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14 AS jdkbase

FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="scala-ansible-vault-shard-hotreload-evaluator"
LABEL org.opencontainers.image.licenses="MIT"

COPY --from=jdkbase /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        findutils \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

ARG SCALA3_VERSION=3.3.4
ARG SCALA3_SHA256=fd0eca29ef1f6c41874b6711e7b6514f1dc7c387c087742fb873f6e720963770
RUN curl -fsSL -o /tmp/scala3.tar.gz \
        "https://github.com/scala/scala3/releases/download/${SCALA3_VERSION}/scala3-${SCALA3_VERSION}.tar.gz" \
    && echo "${SCALA3_SHA256}  /tmp/scala3.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/scala3 \
    && tar -xzf /tmp/scala3.tar.gz -C /opt/scala3 --strip-components=1 \
    && rm -f /tmp/scala3.tar.gz

RUN mkdir -p /opt/vault-libs \
    && curl -fsSL -o /opt/vault-libs/sqlite-jdbc.jar \
        https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.45.3.0/sqlite-jdbc-3.45.3.0.jar \
    && echo "cd55db695548e9b1ba38070109f809052e9ed377256f6218b9e4cd4ee603ab55  /opt/vault-libs/sqlite-jdbc.jar" | sha256sum -c - \
    && curl -fsSL -o /opt/vault-libs/slf4j-api.jar \
        https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.13/slf4j-api-2.0.13.jar \
    && echo "e7c2a48e8515ba1f49fa637d57b4e2f590b3f5bd97407ac699c3aa5efb1204a9  /opt/vault-libs/slf4j-api.jar" | sha256sum -c - \
    && curl -fsSL -o /opt/vault-libs/slf4j-nop.jar \
        https://repo1.maven.org/maven2/org/slf4j/slf4j-nop/2.0.13/slf4j-nop-2.0.13.jar \
    && echo "8962a107b4a8bdf80b6c17e470cd3614ad3329643833ff5cf0c60c7dce9deaac  /opt/vault-libs/slf4j-nop.jar" | sha256sum -c -

COPY requirements-verifier.txt /tmp/requirements-verifier.txt
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir -r /tmp/requirements-verifier.txt \
    && rm -f /tmp/requirements-verifier.txt

WORKDIR /app

COPY app/ /app/

ENV PATH="/opt/scala3/bin:/app/bin:${PATH}"

RUN mkdir -p /app/data /app/output \
    && sed -i 's/\r$//' /app/scripts/build.sh /app/bin/vaultshard-ingest /app/bin/vaultshard-export \
    && chmod +x /app/scripts/build.sh /app/bin/vaultshard-ingest /app/bin/vaultshard-export \
    && /app/scripts/build.sh
