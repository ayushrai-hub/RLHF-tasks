FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        git \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# Install uv and verify binary integrity.
RUN curl -LsSf https://astral.sh/uv/0.11.7/install.sh | sh \
    && echo "cd952ca51e2c730e848a45c4e0dfb58926d79d90550b6a5feb5543b43d3248b4 /root/.local/bin/uv" | sha256sum -c -
# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

RUN uv venv /app/.venv --python 3.13.13
RUN uv pip install --python /app/.venv/bin/python --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"


# Layers above are common for all tasks. Reusing them will speed up the build process.
# Install project dependencies

RUN uv pip install --python /app/.venv/bin/python --no-cache-dir \
    "mlflow==3.12.0" "scikit-learn==1.8.0" "numpy==2.4.6"

RUN uv pip install --python /app/.venv/bin/python --no-cache-dir \
    "onnxruntime==1.26.0" "onnx==1.18.0" "requests==2.34.2"

COPY ./backend/ /app/

RUN npm ci

COPY ./docs/ /app/docs/

# Set environment variables for MLflow
ENV MLFLOW_PORT=5000
