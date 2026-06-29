# Canonical, digest-pinned base (covers Python 3.10-3.13 tasks).
# Platform is pinned to linux/amd64 so the (arch-specific) vendored polars wheel
# always matches the base, regardless of the AutoEval build host's architecture.
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# System packages (single apt transaction):
#   - tmux + asciinema: REQUIRED by the agent runtime to start and record the
#     terminal session. The stock python:3.13-slim-bookworm base does not ship
#     them, so without these every agent run fails at setup with no verifier
#     output (see Dockerfile & Image Best Practices §7).
#   - build-essential + libncurses-dev: REQUIRED by the task itself — the agent
#     extends and compiles the Relic Vault engine (engine/relicvault.c) in
#     milestone 3. Genuine task runtime tools, not a build-only stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        build-essential \
        libncurses-dev \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Verifier + migration-harness runtime deps, hash-pinned for reproducibility.
# polars is a *runtime* dependency (the harness reads parquet/CSV/JSON with it).
# Wheels are VENDORED under environment/vendor/wheels and installed with
# --no-index so the pip step needs ZERO network: the locked-down AutoEval build
# cannot be relied on to serve the large arch-specific polars wheel from a PyPI
# mirror (see Dockerfile & Image Best Practices §7 — all package downloads happen
# at build time / the image must build without network). --require-hashes still
# verifies each local wheel against the lock; the wheels are removed in the same
# layer so they don't bloat the final image.
COPY requirements.lock /tmp/requirements.lock
COPY vendor/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels \
        --require-hashes --no-deps -r /tmp/requirements.lock \
    && rm -rf /tmp/wheels /tmp/requirements.lock

# Bring in the (partially-implemented) codebase the agent must finish.
COPY app/ /app/

# Materialise the binary monster table from its CSV seed, then drop the seed so
# the migrated parquet asset is the only source the harness can read.
RUN python -c "import polars as pl, pathlib; d=pathlib.Path('/app/archive'); pl.read_csv(d/'monsters_seed.csv').write_parquet(d/'monsters.parquet')" \
    && rm /app/archive/monsters_seed.csv

WORKDIR /app
