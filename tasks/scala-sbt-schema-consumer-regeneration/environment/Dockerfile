FROM public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14

USER root
RUN apt-get update     && apt-get install -y --no-install-recommends python3 python3-venv python3-pip tmux asciinema unzip     && rm -rf /var/lib/apt/lists/*     && python3 -m venv /opt/tb-venv     && /opt/tb-venv/bin/python -m pip install --no-cache-dir         pytest==8.4.1         pytest-json-ctrf==0.3.5

ENV PATH="/opt/tb-venv/bin:${PATH}"
WORKDIR /app/environment
COPY --chmod=0755 sbt /app/environment/sbt
COPY build.sbt /app/environment/build.sbt
COPY project /app/environment/project
COPY contracts /app/environment/contracts
COPY consumer /app/environment/consumer
COPY src /app/environment/src
COPY generator /app/environment/generator
COPY docs /app/environment/docs
COPY tools /app/environment/tools
COPY generated /app/environment/generated
