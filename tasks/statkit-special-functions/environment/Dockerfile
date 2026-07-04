# Canonical Terminal-Bench C/C++ runtime base (gcc 13 on Debian bookworm),
# digest-pinned. Provides gcc, make, ar, and libm for building statkit.
FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

# Agent runtime needs tmux + asciinema; the verifier needs python3 + pytest.
# tmux/asciinema are version-pinned to the bookworm release packages; the
# remaining packages are the distro toolchain provided by the pinned base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema=2.2.0-1 \
        ca-certificates \
        make \
        python3 \
        python3-pip \
        python3-venv \
        tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/*

# Verifier dependencies live in an isolated venv (PEP 668 blocks system pip on
# bookworm). The agent solves in C; this venv is only used by tests/test.sh.
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5
ENV PATH="/opt/verifier-venv/bin:${PATH}"

# Guarantee `cc` resolves to the image's gcc (the Makefile and verifier default
# to cc); on the gcc base image cc is not always present.
RUN ln -sf "$(command -v gcc)" /usr/local/bin/cc

WORKDIR /app
COPY app/ /app/

# Validate the shipped stubs compile, then reset to a clean tree, and stash a
# read-only golden copy of the frozen acceptance suite and sample fixtures so
# the verifier can restore them before grading.
RUN cd /app \
    && make all \
    && make clean \
    && mkdir -p /opt/golden \
    && cp -a /app/tests /opt/golden/tests \
    && cp -a /app/data /opt/golden/data
