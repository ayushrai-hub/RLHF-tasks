FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        tmux \
        asciinema \
        curl=7.88.1-10+deb12u14 \
        jq=1.6-2.1+deb12u2 \
        sqlite3=3.40.1-2+deb12u2 \
        ca-certificates=20230311+deb12u1 \
        procps=2:4.0.2-3 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
        Flask==3.0.3 \
        Werkzeug==3.0.4 \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5

COPY app/ /app/

RUN find /app -type f -name "*.sh" -exec chmod +x {} +

ENV API_BASE_URL="http://127.0.0.1:8080" \
    PATH="/app/bin:${PATH}"

CMD ["/app/scripts/entrypoint.sh"]
