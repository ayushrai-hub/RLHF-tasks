.PHONY: all clean d0 tools

CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -Id0 -Ilib

all: d0 tools

d0:
	$(CC) $(CFLAGS) -o d0/cap_drv \
		d0/main.c d0/cap_replay.c d0/cap_emit.c d0/cap_store.c d0/cap_journal.c d0/sha256.c \
		lib/parse_core.c q4_core/main_core.c q4_core/chain_ambient.c q5_stage/pick_main.c

tools: d0
	chmod +x tools/k9_round tools/m2_publish \
		q2_auth/commit.sh q2_auth/tick_log.sh \
		q6_recover/merge_tail.sh \
		q7_launch/sync_path.sh q7_launch/direct_path.sh q7_launch/probe_side.sh \
		q5_stage/sudo_chain.sh q5_stage/step_log.sh \
		q4_core/dump_side.sh q3_nnp/probe_log.sh

clean:
	rm -f d0/cap_drv
