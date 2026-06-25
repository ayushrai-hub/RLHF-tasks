FROM public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383

ENV DATABASE_URL="postgresql://postgres:terminus_pg_pass@localhost:5432/appdb" \
    JWT_SECRET="terminus_jwt_secret_key_at_least_32_chars_long" \
    JWT_EXPIRES_IN="7d" \
    REFRESH_TOKEN_SECRET="terminus_refresh_secret_key_32chars_minimum___" \
    REFRESH_TOKEN_EXPIRES_IN="30d" \
    PORT="3000" \
    LOG_LEVEL="info" \
    WHITE_LIST_URLS="http://localhost:3000" \
    NODE_ENV="development" \
    HUSKY=0

WORKDIR /app

COPY start.sh /start.sh

RUN chmod +x /start.sh \
    && apt-get update && apt-get install -y --no-install-recommends \
        tmux \
        asciinema \
        curl \
        python3=3.11.2-1+b1 \
        python3-pip \
        python3-dev \
        libpq-dev \
        gcc \
        postgresql-15=15.18-0+deb12u1 \
        postgresql-client-15=15.18-0+deb12u1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --break-system-packages \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        requests==2.32.3 \
        psycopg2==2.9.10

COPY repo/package*.json ./
RUN npm ci

COPY repo/ .

# Create .env.dev so env-config.ts doesn't warn about missing file
RUN printf 'DATABASE_URL=postgresql://postgres:terminus_pg_pass@localhost:5432/appdb\nJWT_SECRET=terminus_jwt_secret_key_at_least_32_chars_long\nJWT_EXPIRES_IN=7d\nREFRESH_TOKEN_SECRET=terminus_refresh_secret_key_32chars_minimum___\nREFRESH_TOKEN_EXPIRES_IN=30d\nPORT=3000\nLOG_LEVEL=info\nWHITE_LIST_URLS=http://localhost:3000\nNODE_ENV=development\n' > /app/.env.dev

RUN npx prisma generate

# Set up PostgreSQL, run migrations at build time, then stop postgres
RUN pg_createcluster 15 main 2>/dev/null || true \
    && pg_ctlcluster 15 main start \
    && for i in $(seq 1 30); do pg_isready -q 2>/dev/null && break; sleep 1; done \
    && su postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'terminus_pg_pass';\"" \
    && su postgres -c "psql -c \"CREATE DATABASE appdb;\"" \
    && npx prisma migrate deploy \
    && pg_ctlcluster 15 main stop 2>/dev/null || true

RUN npm run build

EXPOSE 3000
CMD ["/start.sh"]
