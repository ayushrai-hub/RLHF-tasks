FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

# module-proxy-mvs single-step environment
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PATH=/usr/local/go/bin:/go/bin:${PATH}
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ca-certificates tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go && \
    ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt

COPY gomvs-app /app

RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

ENV GOFLAGS=-mod=mod
ENV GOTOOLCHAIN=local

# v9 reviewer fixes 2026-07-04: category -> data-processing, dropped extraneous
# workdir field, robustified the sampler versions test to assert semver ordering
# + a stable known-old subset (no full exact-list pin), and added gofmt -l / go
# vet tests so the stated gofmt/vet-clean requirement is actually enforced.
# v8 difficulty-harden 2026-07-04: removed method-prescribing prose from spec.md,
# instruction.md, CONVENTIONS.md and the mvs BuildList stub comment (SemVer
# precedence derivation, MVS max-version rule, replace-pins-down worked example,
# proxy escaping algorithm, and the etcd/casbin/hugo worked examples). Kept the
# observable contract only: commands, output formats/columns, tokens, exit codes.
# Behavior stays determinable from real Go module tooling semantics; cache-bust.

# ac 1783166181250720487
