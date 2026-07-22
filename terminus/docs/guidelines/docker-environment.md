# Creating Docker Environment

Practical setup guide. Policy details: [dockerfile.md](dockerfile.md).

## Location

`environment/Dockerfile` (or `docker-compose.yaml` for multi-container).

## Starter Dockerfile

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.1.0 requests==2.31.0

COPY app/ /app/
ENV PYTHONPATH=/app
```

## Minimum Checklist

- [ ] Builds successfully
- [ ] tmux + asciinema installed
- [ ] All `FROM` digest-pinned
- [ ] Canonical final base (or justified)
- [ ] Deps exact-pinned
- [ ] apt: `--no-install-recommends` + cleanup
- [ ] `environment/` size limits
- [ ] `.dockerignore` for non-trivial envs
- [ ] No solution/tests in image
- [ ] `allow_internet` set accurately (`false` offline / `true` only if required)
- [ ] Verifier deps in image (not test.sh)
- [ ] No privileged containers

## Patterns

**Python:** `requirements.txt` + pinned pip  
**Node:** `npm ci` with lockfile  
**System admin:** Ubuntu/Debian + services  
**Git repo:** clone at **pinned commit** (prevent cheating)

## Test Locally

```bash
cd environment && docker build -t my-task . && docker run -it my-task bash
harbor tasks start-env -p <task-folder> -i
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails | Check syntax, digest pins, dep versions |
| Permission denied | Docker socket / macOS Advanced settings |
| Missing packages | Add to Dockerfile, rebuild |
