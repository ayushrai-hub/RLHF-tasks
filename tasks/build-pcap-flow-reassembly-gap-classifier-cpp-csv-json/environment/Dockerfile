FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        cmake \
        g++ \
        git \
        make \
        python3 \
        python3-pip \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

WORKDIR /app

COPY CMakeLists.txt /app/CMakeLists.txt
COPY app_entrypoint.py /app/app_entrypoint.py
COPY docs /app/docs
COPY input /app/input
COPY scripts /app/scripts
COPY src /app/src

RUN chmod +x /app/scripts/build.sh && mkdir -p /app/bin

CMD ["python3", "/app/app_entrypoint.py"]
