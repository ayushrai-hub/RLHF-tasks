FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/R/4.4.2/bin:${PATH}"

RUN for i in 1 2 3 4 5; do apt-get update && break || { echo "apt-get update retry $i"; sleep 5; }; done \
 && for i in 1 2 3 4 5; do apt-get install -y --no-install-recommends \
    tmux asciinema \
    python3 python3-pip python3-venv python3-numpy python3-pandas python3-pil \
    ca-certificates curl \
    libfontconfig1-dev libcurl4-openssl-dev libssl-dev libxml2-dev libicu-dev \
    libharfbuzz-dev libfribidi-dev libfreetype6-dev libpng-dev \
    libtiff-dev libjpeg-dev && break || { echo "apt install retry $i"; sleep 5; }; done \
    && curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused -o /tmp/r.deb https://cdn.posit.co/r/debian-12/pkgs/r-4.4.2_1_amd64.deb \
    && echo "3147d94a56234396e7bcd581defbc7f8d7e928d0ac408bc2ff9b80414e74b845  /tmp/r.deb" | sha256sum -c - \
    && apt-get install -y --no-install-recommends /tmp/r.deb \
    && ln -s /opt/R/4.4.2/bin/R /usr/local/bin/R \
    && ln -s /opt/R/4.4.2/bin/Rscript /usr/local/bin/Rscript \
    && rm -f /tmp/r.deb \
    && rm -rf /var/lib/apt/lists/*

RUN R -q -e "\
    options(HTTPUserAgent = sprintf('R/%s R (%s)', getRversion(), paste(getRversion(), R.version[['platform']], R.version[['arch']], R.version[['os']]))); \
    snap <- 'https://packagemanager.posit.co/cran/__linux__/bookworm/2024-12-01'; \
    options(repos = c(CRAN = snap)); \
    options(timeout = 600); \
    pkgs <- list(ggplot2='3.5.1', jsonlite='1.8.9'); \
    for (attempt in 1:5) { \
      try(install.packages(names(pkgs)), silent = TRUE); \
      if (all(sapply(names(pkgs), requireNamespace, quietly = TRUE))) break; \
      Sys.sleep(5) }; \
    missing <- names(pkgs)[!sapply(names(pkgs), requireNamespace, quietly = TRUE)]; \
    if (length(missing) > 0) stop(paste('Failed to install:', paste(missing, collapse = ', '))); \
    for (p in names(pkgs)) { v <- as.character(packageVersion(p)); if (v != pkgs[[p]]) stop(paste('Version drift on', p, ': wanted', pkgs[[p]], 'got', v)) }; \
    if (!requireNamespace('nnet', quietly = TRUE)) stop('nnet not available')"

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv --system-site-packages /opt/verifier-venv \
 && for i in 1 2 3 4 5; do /opt/verifier-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt && break || { echo "pip retry $i"; sleep 5; }; done

WORKDIR /app/environment

COPY data/ /app/environment/data/
COPY analysis.R /app/environment/analysis.R
