LIB = libledger_verify.so
SRC = ledger_verify.c

CFLAGS = -Wall -Wextra -fPIC -O2
LDFLAGS = -shared -lcrypto -licuuc

all: $(LIB)

$(LIB): $(SRC) ledger_verify.h
	$(CC) $(CFLAGS) -o $(LIB) $(SRC) $(LDFLAGS)

clean:
	rm -f $(LIB)

.PHONY: all clean
