FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
WORKDIR /app
# verifier-bake-v2: offline pytest in /opt/verifier

RUN apt-get update && apt-get install -y --no-install-recommends \
  tmux=3.3a-3 \
  asciinema=2.2.0-1 \
  patch=2.7.6-7 \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/verifier
RUN /opt/verifier/bin/pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5
ENV PATH=/opt/verifier/bin:${PATH}

COPY . /app/environment

# Seed the sampled, incomplete logs where the contract says they live.
RUN mkdir -p /app/output/logs \
  && cp /app/environment/logs_seed/probe_scan.log /app/output/logs/probe_scan.log

# Make the toolchain and provided helpers executable.
RUN chmod +x \
  /app/environment/r4/verify_sig.sh \
  /app/environment/r4/dec0.sh \
  /app/environment/r4/legacy_claim.sh \
  /app/environment/r4/stub_pick.sh \
  /app/environment/r4/kx/g_extract_k.sh \
  /app/environment/r5/inv_verify \
  /app/environment/r5/apply_ctl.sh \
  /app/environment/r5/grid_engine.sh \
  /app/environment/r5/stage_only.sh \
  /app/environment/r5/px/g_emit_p.sh \
  /app/environment/r7/rst_step.sh \
  /app/environment/w7/run_entry.sh \
  /app/environment/w7/mx/g_plan_m.sh

CMD ["python3", "-c", "print('Environment ready')"]
