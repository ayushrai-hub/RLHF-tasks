ARCH      := -O2 -mfma
STRICT_FP := -ffp-contract=off
RELEASE_FP := -ffp-contract=fast -fassociative-math -freciprocal-math -fno-signed-zeros -fno-trapping-math -ffinite-math-only

MODE ?= release
ifeq ($(MODE),strict)
FP := $(STRICT_FP)
else
FP := $(RELEASE_FP)
endif

CFLAGS := $(ARCH) $(FP) -Iinclude
SRC := $(wildcard src/*.c)
OBJ := $(patsubst src/%.c,obj/%.o,$(SRC))

kerneltest: $(OBJ) obj/kerneltest.o
	gcc $(ARCH) -o $@ $^ -lm

obj/%.o: src/%.c | obj
	gcc $(CFLAGS) -c $< -o $@

obj/kerneltest.o: tools/kerneltest.c | obj
	gcc $(ARCH) -Iinclude -c $< -o $@

obj:
	mkdir -p obj

clean:
	rm -rf obj kerneltest

.PHONY: clean
