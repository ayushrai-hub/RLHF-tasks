.PHONY: build release test clean

BIN_DIR := bin

build:
	cargo build --release --locked

release: build
	install -d $(BIN_DIR)
	install target/release/streamd $(BIN_DIR)/streamd

test:
	cargo test --workspace --locked

clean:
	rm -rf $(BIN_DIR) target
