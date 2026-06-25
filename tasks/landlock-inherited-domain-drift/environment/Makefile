.PHONY: all clean d0 tools

CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -Id0 -Ilib

all: d0 tools

d0:
	$(CC) $(CFLAGS) -o d0/h7_drv \
		d0/main.c d0/apply_step.c d0/reach_step.c d0/audit_step.c d0/trace_store.c d0/seq_adv.c d0/sha256.c \
		lib/parse_path.c lib/sha256.c \
		r1_apply/stack_layer.c r1_apply/diag_side.c \
		r3_exec/handoff.c r3_exec/log_side.c \
		r5_audit/reflect_row.c r5_audit/format_side.c \
		trace/pack_out.c

tools: d0
	chmod +x tools/k7_round tools/m4_emit \
		tooling/seal_trace.sh \
		q8_actor/wrap_run.sh q8_actor/direct_run.sh q8_actor/probe_side.sh

clean:
	rm -f d0/h7_drv
