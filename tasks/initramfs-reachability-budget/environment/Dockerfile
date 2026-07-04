FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    patch=2.7.6-7 \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    ca-certificates=20230311+deb12u1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier

COPY requirements.txt /opt/verifier/
RUN /opt/verifier/bin/pip install --require-hashes --no-deps -r /opt/verifier/requirements.txt

ENV PATH=/opt/verifier/bin:/usr/local/go/bin:${PATH}
ENV Q7_ENV_ROOT=/app/environment

COPY scripts /app/environment/scripts/
COPY tools /app/environment/tools/
COPY pk_a /app/environment/pk_a/
COPY pk_b /app/environment/pk_b/
COPY pk_c /app/environment/pk_c/
COPY blob_v /app/environment/blob_v/
COPY node_v /app/environment/node_v/
COPY rel_v /app/environment/rel_v/
COPY vstamp_v /app/environment/vstamp_v/
COPY excerpt_v /app/environment/excerpt_v/
COPY fixtures /app/environment/fixtures/
COPY scenarios /app/environment/scenarios/
COPY docs /app/environment/docs/
COPY migrations /app/environment/migrations/
COPY stage /app/environment/stage/
COPY go.mod go.work setup.py /app/environment/

RUN cd /app/environment \
    && bash scripts/build_q7.sh \
    && rm -rf /root/.cache/go-build /root/go/pkg

RUN chmod +x /app/environment/tools/cpio_chk/cpio_chk \
    && chmod +x /app/environment/tools/drv_q7/drv_q7 \
    && chmod +x /app/environment/scripts/build_q7.sh \
    && chmod +x /app/environment/scripts/batch_q7.sh \
    && chmod +x /app/environment/migrations/rst7.sh

RUN mkdir -p /app/output \
    && cp /app/environment/stage/sc_w1_stub.json /app/output/m4_stub.json
