# statkit build
#
#   make all     build the static library and the statctl CLI
#   make lib     build build/libstatkit.a
#   make cli     build build/statctl
#   make test    build and run the acceptance suite in tests/
#   make clean   remove build/
#
# The library is assembled from every src/*.c and the CLI from every cli/*.c,
# so new files are picked up automatically.

CC      ?= cc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra -Iinclude
LDLIBS  ?= -lm

BUILD   := build
LIB     := $(BUILD)/libstatkit.a
CLIBIN  := $(BUILD)/statctl

LIB_SRC  := $(wildcard src/*.c)
LIB_OBJ  := $(patsubst src/%.c,$(BUILD)/obj/%.o,$(LIB_SRC))
CLI_SRC  := $(wildcard cli/*.c)
TEST_SRC := $(wildcard tests/*.c)
TEST_BIN := $(patsubst tests/%.c,$(BUILD)/test/%,$(TEST_SRC))

.PHONY: all lib cli test clean
all: lib cli

lib: $(LIB)

cli: $(CLIBIN)

$(BUILD)/obj/%.o: src/%.c | $(BUILD)/obj
	$(CC) $(CFLAGS) -c $< -o $@

$(LIB): $(LIB_OBJ)
	ar rcs $@ $^

$(CLIBIN): $(CLI_SRC) $(LIB) | $(BUILD)
	$(CC) $(CFLAGS) $(CLI_SRC) -L$(BUILD) -lstatkit $(LDLIBS) -o $@

$(BUILD)/test/%: tests/%.c $(LIB) | $(BUILD)/test
	$(CC) $(CFLAGS) $< -L$(BUILD) -lstatkit $(LDLIBS) -o $@

test: $(TEST_BIN)
	@fail=0; for t in $(TEST_BIN); do echo "== $$t =="; "$$t" || fail=1; done; if [ $$fail -ne 0 ]; then echo "ACCEPTANCE: FAILED"; exit 1; fi; echo "ACCEPTANCE: PASSED"

$(BUILD) $(BUILD)/obj $(BUILD)/test:
	mkdir -p $@

clean:
	rm -rf $(BUILD)
