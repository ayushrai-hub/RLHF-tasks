FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cmake \
        python3 \
        python3-pip \
        tmux \
        asciinema \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


RUN pip3 download --no-cache-dir \
    pytest==9.1.1 \
    pytest-json-ctrf==0.3.5 \
    --dest /opt/test-deps/

WORKDIR /app

# Copy the starter codebase and data artifacts
COPY CMakeLists.txt /app/CMakeLists.txt
COPY src/ /app/src/
COPY data/ /app/data/

# Generate binary scenario files from the Python generator script
RUN python3 /app/data/gen_scenarios.py

# Create output directory for agent artifacts and build directory
RUN mkdir -p /app/out /app/build
