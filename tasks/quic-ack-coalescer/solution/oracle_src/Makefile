.PHONY: build clean

BIN=/app/bin/qack

build:
	@mkdir -p /app/bin
	@cd /app && /usr/local/go/bin/go build -trimpath -o $(BIN) ./cmd/qack

clean:
	@rm -f $(BIN)
