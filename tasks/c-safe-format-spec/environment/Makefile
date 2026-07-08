CC ?= gcc
CFLAGS ?= -std=c11 -O0 -g -Wall -Wextra -Iinclude
LDFLAGS ?=

SOURCES := $(wildcard src/*.c) cmd/sfmt/main.c
OBJECTS := $(SOURCES:.c=.o)
TARGET := sfmt

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJECTS) $(TARGET)

.PHONY: all clean
