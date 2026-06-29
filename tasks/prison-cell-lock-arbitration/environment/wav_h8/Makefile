CC ?= gcc
CFLAGS ?= -Wall -Wextra -fPIC
INCLUDES = -Iinclude

.PHONY: all clean

all: libwav_h8.a

libwav_h8.a: src/t8.o src/wave.o src/diag.o
	ar rcs $@ $^

src/%.o: src/%.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f src/*.o libwav_h8.a
