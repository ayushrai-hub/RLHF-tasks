.PHONY: glyphvault-analyze clean

CC ?= gcc
CFLAGS = -std=c11 -Wall -Wextra -O2 -Iinclude
LDFLAGS = -lsqlite3 -lpng -lm

SRC = src/db_open.c src/alias_resolver.c src/clue_query.c src/meta_decoder.c \
	src/glyph_atlas.c src/direction_map.c src/unlock_gate.c src/score_engine.c \
	src/move_driver.c src/room_engine.c src/transcript_writer.c src/tf_output_reader.c \
	src/main.c

build/glyphvault_analyze: $(SRC)
	@mkdir -p build
	$(CC) $(CFLAGS) -o build/glyphvault_analyze $(SRC) $(LDFLAGS)

glyphvault-analyze: build/glyphvault_analyze

clean:
	rm -rf build
