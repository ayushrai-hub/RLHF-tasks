FROM debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends python3=3.11.2-1+b1 python3-pip=23.0.1+dfsg-1 \
    asciinema=2.2.0-1 \
    build-essential=12.9 \
    ca-certificates=20230311+deb12u1 \
    cmake=3.25.1-1 \
    g++=4:12.2.0-3 \
    make=4.3-4.1 \
    tmux=3.3a-3 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY CMakeLists.txt /app/CMakeLists.txt
COPY include /app/include
COPY core /app/core
COPY mpi /app/mpi
COPY io /app/io
COPY sim /app/sim
COPY util /app/util
COPY data /app/data
COPY config /app/config
COPY docs /app/docs
COPY main.cpp /app/main.cpp

RUN mkdir -p /app/bin /app/output
RUN ln -s /app /app/environment
RUN cmake -S /app -B /app/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /app/build -j2 \
    && cp /app/build/tb_iter /usr/local/bin/tb_iter

ENV PATH="/app/bin:${PATH}"
