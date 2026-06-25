.PHONY: build clean run verify

# Defensive go path: if `go` is not on PATH (e.g. a stripped interactive
# shell), fall back to the well-known install location at /usr/local/go.
GO ?= $(shell command -v go 2>/dev/null || echo /usr/local/go/bin/go)
GOCACHE ?= /tmp/go-cache
GOPATH ?= /tmp/go-path

build:
	rm -rf /app/bin
	mkdir -p /app/bin $(GOCACHE) $(GOPATH)
	cd /app && GOCACHE=$(GOCACHE) GOPATH=$(GOPATH) GOFLAGS=-mod=mod GOPROXY=off GOTOOLCHAIN=local CGO_ENABLED=0 $(GO) build -trimpath -o /app/bin/auditor ./cmd/auditor

# `make run` rebuilds and runs the auditor against the primary fixture.
# Useful for fast iteration without invoking pytest. Prints the binary
# exit code; the report lands at /app/output/report.json.
run: build
	@/app/bin/auditor --data /app/data --out /app/output/report.json
	@echo "rc=$$?"
	@ls -la /app/output/

# `make verify` rebuilds, runs, and pretty-prints a one-line summary of
# total_probes, aligned_good, cycles, and report_digest so the agent
# can spot-check key invariants without a full pytest invocation.
verify: build
	@/app/bin/auditor --data /app/data --out /app/output/report.json
	@python3 -c "import json; d=json.load(open('/app/output/report.json')); print('total_probes:', d['summary']['total_probes']); print('aligned_good:', d['summary']['aligned_good']); print('cycles:', d['summary']['cycles']); print('by_verdict:', d['summary']['by_verdict']); print('jitter_share_permille:', d['summary']['jitter_share_permille']); print('report_digest:', d['summary']['report_digest']); print('cycle thresholds:', [(c['cycle_id'], c['threshold_owd_us']) for c in d['cycles']])"

clean:
	rm -rf /app/bin
