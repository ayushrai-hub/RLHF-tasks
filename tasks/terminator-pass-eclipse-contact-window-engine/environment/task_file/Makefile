.PHONY: clean build

clean:
	rm -f /app/contact

build:
	cd /app/src && GOFLAGS=-mod=mod GOPROXY=off go build -o /app/contact .
