# Hint from Snorkel
# Base Dockerfile or image that fully sets up the environment, including all required tools, resources, and dependencies.
# It should be reproducible, lightweight, and run without privileged mode.

FROM python:3.13-slim-bookworm

WORKDIR /app

# Only copy application files into the image (never tests/ or solution/).
COPY app/ /app/

# Run as non-root to avoid privileged assumptions.
RUN useradd -m -u 1001 ciuser \
  && chown -R ciuser:ciuser /app \
  && mkdir -p /logs/agent /logs/verifier /app/output/chunks \
  && chown -R ciuser:ciuser /logs /app/output \
  && chmod -R 0777 /logs

USER ciuser
