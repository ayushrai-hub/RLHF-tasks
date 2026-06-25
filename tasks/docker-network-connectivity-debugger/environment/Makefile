.PHONY: build run clean

GO := /usr/local/go/bin/go
BINARY := /app/build/docker-network-connectivity-debugger

build:
	@mkdir -p /app/build
	cd /app && $(GO) build -o build/docker-network-connectivity-debugger ./cmd/docker-network-connectivity-debugger

run: build
	/app/build/docker-network-connectivity-debugger

clean:
	rm -f /app/build/docker-network-connectivity-debugger /app/build/docker_network_connectivity_debugger_report.json
