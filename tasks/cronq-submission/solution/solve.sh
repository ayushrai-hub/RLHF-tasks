#!/bin/bash
set -euo pipefail

# Six independent fixes, each applied through Python
# so a replacement that no longer matches the source fails loudly
# instead of leaving the bug in place.
python3 - <<'PY'
matcher = "/app/src/com/cronq/match/Matcher.java"
parser  = "/app/src/com/cronq/parse/FieldParser.java"
calc    = "/app/src/com/cronq/calc/NextCalculator.java"

# Fix 1: the day rule.
# When both day-of-month and day-of-week are restricted, PROTOCOL.md
# section 2 says the two are OR'd -- a time fires if it matches either field.
# The code had them AND'd, which only fires when both agree (e.g. only
# Fridays that are also the 13th), so it drops most of the days it
# should hit.
with open(matcher) as f:
    src = f.read()
fixed = src.replace(
    "            return domOk && dowOk;",
    "            return domOk || dowOk;",
)
assert fixed != src, "Matcher.java: day-rule patch did not match"
with open(matcher, "w") as f:
    f.write(fixed)

# Fix 2: the day-of-week mapping.
# java.time numbers days MON=1 .. SUN=7; the cron convention in
# PROTOCOL.md section 1 is SUN=0 .. SAT=6. The two agree for Monday
# through Saturday, which is why nothing looked wrong, but a Sunday
# comes back as 7 and never matches a day-of-week set built around 0.
# Map it down before the lookup.
with open(matcher) as f:
    src = f.read()
fixed = src.replace(
    "        int cronDow = t.getDayOfWeek().getValue();",
    "        // java DayOfWeek is MON=1..SUN=7; cron wants SUN=0..SAT=6.\n"
    "        int cronDow = t.getDayOfWeek().getValue() % 7;",
)
assert fixed != src, "Matcher.java: day-of-week mapping patch did not match"
with open(matcher, "w") as f:
    f.write(fixed)

# Fix 3: a lone value with a step.
# `9/3` means start at 9 and step by 3 up to the field max. The low end
# of that series is the value itself, 9 -- not the bottom of the field.
# The code reset the low end to the field minimum whenever a step was
# present, so `9/3` started counting from 0.
with open(parser) as f:
    src = f.read()
fixed = src.replace(
    "            lo = (slash >= 0) ? min : v;",
    "            lo = v;",
)
assert fixed != src, "FieldParser.java: lone-value-step patch did not match"
with open(parser, "w") as f:
    f.write(fixed)

# Fix 4: a range with a step.
# `a-b/k` steps across the written range a to b -- the high end is b, the
# top of the range, not the field maximum. The code stretched the high
# end to the field max whenever a step was present, so a term like
# `1-25/7` kept stepping past 25 to the end of the field.
with open(parser) as f:
    src = f.read()
fixed = src.replace(
    "            hi = (slash >= 0) ? max : value(base.substring(dash + 1), names);",
    "            hi = value(base.substring(dash + 1), names);",
)
assert fixed != src, "FieldParser.java: range-step patch did not match"
with open(parser, "w") as f:
    f.write(fixed)

# Fix 5: "strictly after".
# The next fire time has to be strictly after `from`; a schedule that
# fires exactly at `from` should report the following occurrence
# (PROTOCOL.md section 3). The search started its cursor on the floored
# start minute itself, so a `from` sitting on a fire minute got counted
# as its own next time. Step one minute past the floored start.
with open(calc) as f:
    src = f.read()
fixed = src.replace(
    "        LocalDateTime cursor = start;",
    "        LocalDateTime cursor = start.plusMinutes(1);",
)
assert fixed != src, "NextCalculator.java: strictly-after patch did not match"
with open(calc, "w") as f:
    f.write(fixed)

# Fix 6: the minute on an hour jump.
# When the search settles on a later hour than the cursor was sitting in,
# the minute has to land on the minute field's lowest allowed value, not
# on a literal 0. They coincide whenever the field allows minute 0, which
# hides the bug, but a schedule like `45 6 * * *` then reports 06:00 -- a
# minute it never fires on. Reset to the field's own floor instead.
with open(calc) as f:
    src = f.read()
fixed = src.replace(
    "return t.withHour(h).withMinute(0);",
    "return t.withHour(h).withMinute(e.minute.values().iterator().next());",
).replace(
    "return t.withHour(hn).withMinute(0);",
    "return t.withHour(hn).withMinute(e.minute.values().iterator().next());",
)
assert fixed != src, "NextCalculator.java: minute-floor patch did not match"
with open(calc, "w") as f:
    f.write(fixed)
PY

cd /app
./build.sh

# Quick smoke check: daily-midnight starts the day after an on-the-minute
# start once the strictly-after fix is in.
out=$(java -jar /app/cronq.jar next --expr "0 0 * * *" --from "2026-03-01T00:00:00Z" --count 1)
echo "$out" | grep -q '2026-03-02T00:00:00Z' \
  || { echo "smoke check failed: $out" >&2; exit 1; }

echo "solve.sh complete"
