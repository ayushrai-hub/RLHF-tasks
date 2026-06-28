.PHONY: build install smoke clean

BIN := /usr/local/bin/nsx

build:
	go build ./...

install:
	go build -o $(BIN) ./cmd/nsx

smoke: install
	rm -rf /tmp/nsx-smoke
	mkdir -p /tmp/nsx-smoke
	$(BIN) build --input samples/visible.xml --out /tmp/nsx-smoke
	$(BIN) validate --input samples/visible.xml --artifact /tmp/nsx-smoke
	cat /tmp/nsx-smoke/canonical.xml

clean:
	rm -rf /tmp/nsx-smoke /app/output/nsx-run
