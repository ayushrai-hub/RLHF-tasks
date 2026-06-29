CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -Iinclude -I../pkt_vend/include -I../c8_wrap/include
LDFLAGS ?= -lcurl -lssl -lcrypto

DRV_SRCS = src/main.c src/http_client.c src/vault_io.c src/stub_op_a.c \
           src/bind_bridge.c src/enroll_cmd.c src/mfa_cmd.c src/verify_cmd.c \
           src/probe_cmd.c
STORE_SRCS = ../c7_rack/src/op_a.c ../c7_rack/src/op_a_support.c
PKT_SRCS = ../pkt_vend/src/emit_b.c ../pkt_vend/src/step_bridge.c \
           ../pkt_vend/src/lane_sync.c ../pkt_vend/src/lane_blend.c \
           ../pkt_vend/src/counter_pack.c
W4_SRCS = ../c8_wrap/src/resolve_c.c ../c8_wrap/src/seal_bridge.c \
          ../c8_wrap/src/mac_segment.c
SRCS = $(DRV_SRCS) $(STORE_SRCS) $(PKT_SRCS) $(W4_SRCS)
OBJS = $(DRV_SRCS:.c=.o) $(STORE_SRCS:.c=.o) $(PKT_SRCS:.c=.o) $(W4_SRCS:.c=.o)
BIN = /app/bin/m3_cli

.PHONY: all clean

all: $(BIN)

$(BIN): $(OBJS)
	mkdir -p /app/bin
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

src/%.o: src/%.c include/k9.h
	$(CC) $(CFLAGS) -c -o $@ $<

../c7_rack/src/%.o: ../c7_rack/src/%.c include/k9.h
	$(CC) $(CFLAGS) -c -o $@ $<

../pkt_vend/src/%.o: ../pkt_vend/src/%.c include/k9.h
	$(CC) $(CFLAGS) -c -o $@ $<

../c8_wrap/src/%.o: ../c8_wrap/src/%.c include/k9.h
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(BIN)
