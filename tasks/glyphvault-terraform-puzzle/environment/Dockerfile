FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
        gcc \
        libc6-dev \
        make \
        libsqlite3-dev \
        libpng-dev \
        sqlite3 \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip \
        -o /tmp/terraform.zip \
    && echo "186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8  /tmp/terraform.zip" | sha256sum -c - \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

ENV TF_CLI_CONFIG_FILE=/app/environment/terraform/.terraformrc

WORKDIR /app

COPY Makefile README.md /app/environment/
COPY config/ /app/environment/config/
COPY bin/ /app/environment/bin/
COPY include/ /app/environment/include/
COPY src/ /app/environment/src/
COPY lib/ /app/environment/lib/
COPY docs/ /app/environment/docs/
COPY media/ /app/environment/media/
COPY data/ /app/environment/data/
COPY scripts/ /app/environment/scripts/
COPY share/ /app/environment/share/
COPY terraform/ /app/environment/terraform/

RUN chmod +x /app/environment/terraform/provider-mirror/registry.terraform.io/hashicorp/null/3.2.2/linux_amd64/terraform-provider-null_v3.2.2_x5

RUN mkdir -p /app/environment/build /app/environment/artifacts \
    && sed -i 's/\r$//' /app/environment/bin/* \
    && chmod +x /app/environment/bin/puzzle-analyze /app/environment/bin/apply-terraform-fixture.sh \
    && make -C /app/environment glyphvault-analyze

ENV PATH="/app/environment/bin:${PATH}"
