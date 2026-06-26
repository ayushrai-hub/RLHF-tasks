.PHONY: build test serial probe
build:
	./scripts/build.sh
test:
	go test ./internal/ward/ -v -count=1
serial:
	go run ./cmd/probe/main.go
