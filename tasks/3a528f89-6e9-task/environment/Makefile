CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -I/app/environment/tools
LDFLAGS ?=

TOOLS_OBJS = tools/dig01.o
LOAD_OBJS = load_r8/merge_r8.o load_r8/shadow_note.o
SCAN_OBJS = scan_k3/walk_k3.o scan_k3/main_only.o
LINK_OBJS = link_t2/link_emit.o link_t2/legacy_flags.o
TRACE_OBJS = trace/pack_z4.o trace/chain_io.o trace/persist_v5.o
BRIDGE_OBJS = bridge/harness_core.o bridge/scan_face.o bridge/emit_face.o \
	bridge/stage_load.o bridge/stage_link.o

.PHONY: all clean

all: /app/bin/h02_batch

/app/bin/h02_batch: $(TOOLS_OBJS) $(LOAD_OBJS) $(SCAN_OBJS) $(LINK_OBJS) $(TRACE_OBJS) $(BRIDGE_OBJS)
	@mkdir -p /app/bin
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

tools/dig01.o: tools/dig01.c tools/dig01.h
	$(CC) $(CFLAGS) -c -o $@ tools/dig01.c

load_r8/merge_r8.o: load_r8/merge_r8.c tools/dig01.h
	$(CC) $(CFLAGS) -c -o $@ load_r8/merge_r8.c

load_r8/shadow_note.o: load_r8/shadow_note.c
	$(CC) $(CFLAGS) -c -o $@ load_r8/shadow_note.c

scan_k3/walk_k3.o: scan_k3/walk_k3.c tools/dig01.h
	$(CC) $(CFLAGS) -c -o $@ scan_k3/walk_k3.c

scan_k3/main_only.o: scan_k3/main_only.c tools/dig01.h
	$(CC) $(CFLAGS) -c -o $@ scan_k3/main_only.c

link_t2/link_emit.o: link_t2/link_emit.c
	$(CC) $(CFLAGS) -c -o $@ link_t2/link_emit.c

link_t2/legacy_flags.o: link_t2/legacy_flags.c
	$(CC) $(CFLAGS) -c -o $@ link_t2/legacy_flags.c

trace/pack_z4.o: trace/pack_z4.c
	$(CC) $(CFLAGS) -c -o $@ trace/pack_z4.c

trace/chain_io.o: trace/chain_io.c trace/chain_io.h tools/dig01.h
	$(CC) $(CFLAGS) -c -o $@ trace/chain_io.c

trace/persist_v5.o: trace/persist_v5.c trace/persist_v5.h
	$(CC) $(CFLAGS) -c -o $@ trace/persist_v5.c

bridge/harness_core.o: bridge/harness_core.c tools/dig01.h trace/persist_v5.h
	$(CC) $(CFLAGS) -c -o $@ bridge/harness_core.c

bridge/scan_face.o: bridge/scan_face.c
	$(CC) $(CFLAGS) -c -o $@ bridge/scan_face.c

bridge/emit_face.o: bridge/emit_face.c
	$(CC) $(CFLAGS) -c -o $@ bridge/emit_face.c

bridge/stage_load.o: bridge/stage_load.c
	$(CC) $(CFLAGS) -c -o $@ bridge/stage_load.c

bridge/stage_link.o: bridge/stage_link.c
	$(CC) $(CFLAGS) -c -o $@ bridge/stage_link.c

clean:
	rm -f $(TOOLS_OBJS) $(LOAD_OBJS) $(SCAN_OBJS) $(LINK_OBJS) $(TRACE_OBJS) $(BRIDGE_OBJS) /app/bin/h02_batch
