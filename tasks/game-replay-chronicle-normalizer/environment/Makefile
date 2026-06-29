.PHONY: all build clean

BIN := /app/bin/replay-chronicle

all: build

build:
	go build -mod=vendor -o $(BIN) ./cmd/replay-chronicle

clean:
	rm -f $(BIN)
