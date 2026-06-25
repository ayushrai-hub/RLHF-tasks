FROM public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df

# tmux + asciinema power the agent runtime; jq, curl, procps for orchestration;
# perl is the deliverable client's language (core perl gives HTTP::Tiny + JSON::PP);
# python3 for the verifier; sqlite3 for the case database.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tmux=3.3a-3 \
        asciinema=2.2.0-1 \
        curl=7.88.1-10+deb12u14 \
        ca-certificates=20230311+deb12u1 \
        jq=1.6-2.1+deb12u1 \
        procps=2:4.0.2-3 \
        iproute2=6.1.0-3 \
        perl \
        python3=3.11.2-1+b1 \
        python3-pip=23.0.1+dfsg-1 \
        build-essential=12.9 \
        libyaml-dev=0.2.5-1 \
        libsqlite3-dev=3.40.1-2+deb12u2 \
        sqlite3=3.40.1-2+deb12u2 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        requests==2.32.3

ENV BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_WITHOUT="development:test" \
    RAILS_ENV=production \
    RAILS_LOG_TO_STDOUT=1

COPY api/ /app/api/
COPY dossier/ /app/dossier/
COPY data/ /app/data/

RUN cd /app/api \
    && gem install bundler -v 2.5.23 --no-document \
    && bundle config set --local without 'development test' \
    && bundle install --jobs=4 \
    && bundle clean --force \
    && mkdir -p /app/api/db \
    && sqlite3 /app/api/db/case.sqlite3 < /app/api/db/seed.sql \
    && chmod 0644 /app/api/db/case.sqlite3 \
    && rm -f /app/api/db/seed.sql

WORKDIR /app

# Base image inherits CMD=[irb]; reset so any harness override that drops
# only the command lands on bash, not the Ruby REPL.
CMD ["bash"]
