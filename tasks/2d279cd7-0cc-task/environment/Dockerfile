FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

WORKDIR /app

# Install system dependencies with exact point-in-time pins
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3=3.11.2-1+b1 \
    python3-venv=3.11.2-1+b1 \
    tmux=3.3a-3 \
    asciinema=2.2.0-1 \
    patch=2.7.6-7 \
    && rm -rf /var/lib/apt/lists/*

# Set up virtual environment and install verifier dependencies
RUN python3 -m venv /opt/verifier
COPY requirements.txt /tmp/requirements.txt
RUN /opt/verifier/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt

ENV PATH=/opt/verifier/bin:${PATH}
ENV PYTHONPATH=/app

# Create required directories
RUN mkdir -p /app/src/lib /app/data /app/docs /app/output

# Copy files
COPY . /app

CMD ["node", "src/main.js"]
