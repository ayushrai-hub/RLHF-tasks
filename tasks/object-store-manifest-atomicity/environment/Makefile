BIN := $(CURDIR)/bin/ostore
STORE := /app/work/object-store
OUT := /app/output

.PHONY: build clean replay-smoke fixture rebuild smoke doctor test

build:
	mkdir -p $(dir $(BIN))
	go build -trimpath -o $(BIN) ./cmd/ostore

clean:
	rm -rf /app/environment/bin $(STORE) $(OUT)

fixture: build
	rm -rf $(STORE)
	mkdir -p /app/work
	$(BIN) fixture --scenario crash-retry --store $(STORE)

rebuild: build
	mkdir -p $(OUT)
	$(BIN) rebuild --store $(STORE) --out $(OUT)

smoke: build
	$(BIN) smoke --store $(STORE) --out $(OUT)

replay-smoke: build
	rm -rf $(STORE) $(OUT)
	mkdir -p /app/work $(OUT)
	$(BIN) fixture --scenario crash-retry --store $(STORE)
	$(BIN) rebuild --store $(STORE) --out $(OUT)
	$(BIN) smoke --store $(STORE) --out $(OUT)
	$(BIN) doctor --store $(STORE) > $(OUT)/doctor.log
	tail -n +1 $(OUT)/doctor.log

test: build
	go test ./...
