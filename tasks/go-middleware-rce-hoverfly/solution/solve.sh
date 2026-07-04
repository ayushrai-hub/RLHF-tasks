#!/bin/bash

cd /app/environment

if ! patch -p1 < /solution/patches/middleware_config.go.patch; then
    echo "oracle: FAILED to apply middleware_config.go.patch" >&2
    exit 1
fi
if ! patch -p1 < /solution/patches/middleware_local_exec.go.patch; then
    echo "oracle: FAILED to apply middleware_local_exec.go.patch" >&2
    exit 1
fi
if ! patch -p1 < /solution/patches/middleware_remote_exec.go.patch; then
    echo "oracle: FAILED to apply middleware_remote_exec.go.patch" >&2
    exit 1
fi
if ! patch -p1 < /solution/patches/middleware_service.go.patch; then
    echo "oracle: FAILED to apply middleware_service.go.patch" >&2
    exit 1
fi
if ! patch -p1 < /solution/patches/service_auth.go.patch; then
    echo "oracle: FAILED to apply service_auth.go.patch" >&2
    exit 1
fi

cp /solution/security_notes.md /app/environment/security_notes.md

mkdir -p /app/environment/bin

if ! go build -o /app/environment/bin/mwtool ./cmd/mwtool; then
    echo "oracle: FAILED to build mwtool" >&2
    exit 1
fi
if ! go build -o /app/environment/bin/mw-runner ./cmd/mw-runner; then
    echo "oracle: FAILED to build mw-runner" >&2
    exit 1
fi

echo "oracle: solve.sh complete"
