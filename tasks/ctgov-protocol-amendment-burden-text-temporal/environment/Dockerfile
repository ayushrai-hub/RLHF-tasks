FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN printf 'Acquire::http::Timeout "120";\nAcquire::https::Timeout "120";\nAcquire::Retries "5";\n' > /etc/apt/apt.conf.d/99-robust-fetch \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        gfortran \
        libcurl4-openssl-dev \
        libssl-dev \
        libxml2-dev \
        r-base \
        r-base-dev \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# jsonlite and rpart come from a frozen Posit Package Manager snapshot, so the
# resolved versions are reproducible; the snapshot date is the pin.
RUN R -e "options(HTTPUserAgent = sprintf('R/%s R (%s)', getRversion(), paste(getRversion(), R.version['platform'], R.version['arch'], R.version['os']))); \
    options(repos = 'https://packagemanager.posit.co/cran/__linux__/bookworm/2024-12-01'); \
    install.packages(c('jsonlite', 'rpart'), Ncpus = 2); \
    missing <- setdiff(c('jsonlite', 'rpart'), rownames(installed.packages())); \
    if (length(missing) > 0L) { message('R PACKAGES FAILED TO INSTALL: ', paste(missing, collapse = ', ')); quit(status = 1L) }; \
    message('R package versions: jsonlite ', packageVersion('jsonlite'), ', rpart ', packageVersion('rpart'))"

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.lock

COPY data/ /app/data/
COPY helpers/ /app/helpers/
COPY task_contract.md /app/task_contract.md

RUN mkdir -p /app/data /app/helpers /app/output
WORKDIR /app
