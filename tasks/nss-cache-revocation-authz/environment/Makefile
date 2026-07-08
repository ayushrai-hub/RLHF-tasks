BIN := bin/authzctl
PKG := ./cmd/authzctl

.PHONY: build clean run-visible

build:
	mkdir -p bin
	go build -trimpath -o $(BIN) $(PKG)

clean:
	rm -rf bin /app/output/authorization-trace.json /app/work/authz-state

run-visible: build
	mkdir -p /app/output /app/work/authz-state
	./$(BIN) run-case --case fixtures/cases/desk-basic.json --state /app/work/authz-state --out /app/output/authorization-trace.json
