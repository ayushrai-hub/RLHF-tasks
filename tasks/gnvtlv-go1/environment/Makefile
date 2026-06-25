.PHONY: build test fmt clean

BIN := bin/gnvtlv

build:
	@mkdir -p bin
	go build -o $(BIN) ./cmd/gnvtlv

test:
	go test ./...

fmt:
	gofmt -w .

clean:
	rm -rf bin
