FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

ENV PATH="/usr/local/cargo/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip tmux asciinema && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY Cargo.toml Cargo.lock build.rs /app/
RUN mkdir src && echo "fn main(){}" > src/main.rs && cargo build --release --locked && rm -rf src

COPY src/ /app/src/
RUN touch src/main.rs && cargo build --release --locked

COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY scripts/ /app/scripts/
COPY benchmarks/ /app/benchmarks/

RUN mkdir -p /app/output

RUN echo 'export PATH="/usr/local/cargo/bin:$PATH"' >> /root/.bashrc
