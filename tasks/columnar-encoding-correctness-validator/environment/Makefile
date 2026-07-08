SHELL := /bin/bash

BIN_DIR := /app/bin
VALIDATOR_BIN := $(BIN_DIR)/columnar-validator
OUT_DIR := /app/output
REPORT := $(OUT_DIR)/encoding_integrity_report.json

GO ?= go
GOFLAGS ?= -trimpath
LDFLAGS ?= -s -w

.PHONY: all build run clean tidy verify

all: build

build: $(BIN_DIR)
	$(GO) build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o $(VALIDATOR_BIN) ./validator

run: build
	mkdir -p $(OUT_DIR)
	$(VALIDATOR_BIN)

clean:
	rm -rf $(BIN_DIR)/columnar-validator $(REPORT)

tidy:
	$(GO) mod tidy

verify:
	test -x $(VALIDATOR_BIN)
	test -s $(REPORT)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)
