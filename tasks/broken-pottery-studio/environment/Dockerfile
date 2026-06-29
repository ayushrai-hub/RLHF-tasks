FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
LABEL harbor.rebuild="7"
RUN apt-get update && apt-get install -y --no-install-recommends tmux && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 requests==2.32.3 asciinema==2.4.0

WORKDIR /app

COPY audit_log.py availability_service.py cache.py circuit_breaker.py data.py event_store.py lock_manager.py pagination.py pricing_service.py rate_limiter.py refund_policy.py repository.py reservation.py reservation_system.py retry.py student.py studio.py studio_gateway.py time_provider.py waitlist_service.py analytics_service.py notification_service.py reporting_service.py /app/
ENV PYTHONPATH=/app
