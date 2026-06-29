CC      ?= gcc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra -DWITH_NCURSES
LDLIBS  ?= -lncurses

OBJ = relicvault.o legacy_rooms.o

relicvault: $(OBJ)
	$(CC) $(CFLAGS) -o relicvault $(OBJ) $(LDLIBS)

relicvault.o: relicvault.c legacy_rooms.h
	$(CC) $(CFLAGS) -c -o $@ relicvault.c

legacy_rooms.o: legacy_rooms.c legacy_rooms.h
	$(CC) $(CFLAGS) -c -o $@ legacy_rooms.c

clean:
	rm -f $(OBJ) relicvault

.PHONY: clean
