CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2 -I/app/environment/include -I/app/environment/src
LDFLAGS = -lm

SRCS = \
  src/main.c \
  src/parse/interval_csv.c \
  src/parse/config_load.c \
  src/schedule/season.c \
  src/schedule/tou_lookup.c \
  src/schedule/tier_context.c \
  src/aggregate/demand_track.c \
  src/aggregate/gap_elapsed.c \
  src/aggregate/interval_energy.c \
  src/aggregate/meter_roll.c \
  src/reconcile/report.c \
  src/util/strutil.c \
  src/util/timezone.c

OBJS = $(SRCS:.c=.o)

all: /app/bin/tou_reconcile

/app/bin/tou_reconcile: $(OBJS)
	mkdir -p /app/bin /app/output
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

%.o: /app/environment/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) /app/bin/tou_reconcile

.PHONY: all clean
