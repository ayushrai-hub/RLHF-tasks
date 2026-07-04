.PHONY: build audit clean

BINARY := /app/build/driftaudit

build:
	@mkdir -p /app/build
	cd /app && /usr/local/go/bin/go build -o build/driftaudit ./bin/driftaudit

audit: build
	/app/build/driftaudit

clean:
	rm -f /app/build/driftaudit /app/build/drift_audit_report.json
