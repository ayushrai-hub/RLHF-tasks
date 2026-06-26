FROM python:3.12-bookworm@sha256:218a88a57964084b18fe70190b9d5cc6543b24126c3206c3d3e707db8e0c3c25

RUN apt-get update &&     apt-get install -y --no-install-recommends         python3=3.11.2-1+b1         python3-pip=23.0.1+dfsg-1         tmux=3.3a-3 &&     rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1

WORKDIR /app
COPY app/ /app/
RUN mkdir -p /opt/tool-context && cp -a /app/context/. /opt/tool-context/ && rm -rf /app/context
RUN chmod +x /app/bin/context-lookup && ln -sf /app/bin/context-lookup /usr/local/bin/context-lookup
RUN mkdir -p /app/output
CMD ["/bin/bash"]
